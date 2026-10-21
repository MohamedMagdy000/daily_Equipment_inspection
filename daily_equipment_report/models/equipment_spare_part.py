from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta


class EquipmentSparePart(models.Model):
    _name = "equipment.spare.part"
    _description = "Equipment Spare Part"
    _order = "next_maintenance_date, equipment_id, name"
    _check_company_auto = True

    name = fields.Char(string="Spare Part Name", required=True, translate=True)
    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        string="Equipment",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="equipment_id.company_id",
        store=True,
        readonly=True,
    )
    category_id = fields.Many2one(
        related="equipment_id.category_id",
        store=True,
        readonly=True,
        string="Equipment Category",
    )
    last_maintenance_date = fields.Date(
        string="Last Maintenance Date",
        required=True,
        default=fields.Date.context_today,
    )
    maintenance_cycle_days = fields.Integer(
        string="Maintenance Cycle (Days)",
        default=90,
        required=True,
        help="Number of days after which this part is due for maintenance again.",
    )
    next_maintenance_date = fields.Date(
        string="Next Maintenance Date",
        compute="_compute_next_maintenance_date",
        store=True,
        index=True,
    )
    maintenance_state = fields.Selection(
        selection=[
            ("healthy", "Healthy"),
            ("due_soon", "Due Soon"),
            ("overdue", "Overdue"),
        ],
        string="Maintenance Status",
        compute="_compute_maintenance_state",
    )
    reminder_sent = fields.Boolean(
        string="Reminder Sent",
        default=False,
        copy=False,
        help="Technical field used to prevent duplicate reminder activities.",
    )
    active = fields.Boolean(default=True)

    @api.depends("last_maintenance_date", "maintenance_cycle_days")
    def _compute_next_maintenance_date(self):
        for part in self:
            if part.last_maintenance_date and part.maintenance_cycle_days > 0:
                part.next_maintenance_date = part.last_maintenance_date + timedelta(
                    days=part.maintenance_cycle_days
                )
            else:
                part.next_maintenance_date = False

    @api.depends("next_maintenance_date")
    def _compute_maintenance_state(self):
        today = fields.Date.context_today(self)
        warning_date = today + timedelta(days=7)
        for part in self:
            if not part.next_maintenance_date or part.next_maintenance_date > warning_date:
                part.maintenance_state = "healthy"
            elif part.next_maintenance_date < today:
                part.maintenance_state = "overdue"
            else:
                part.maintenance_state = "due_soon"

    @api.constrains("maintenance_cycle_days")
    def _check_maintenance_cycle_days(self):
        for part in self:
            if part.maintenance_cycle_days <= 0:
                raise ValidationError(_("The maintenance cycle must be greater than zero days."))

    def write(self, vals):
        if "last_maintenance_date" in vals or "maintenance_cycle_days" in vals:
            vals.setdefault("reminder_sent", False)
        return super().write(vals)

    @api.model
    def _cron_check_maintenance_due(self):
        today = fields.Date.context_today(self)
        due_parts = self.search([
            ("active", "=", True),
            ("next_maintenance_date", "<=", today),
            ("reminder_sent", "=", False),
        ])
        for part in due_parts:
            equipment = part.equipment_id
            responsible_user = equipment.owner_user_id or equipment.technician_user_id or self.env.user
            equipment.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=today,
                summary=_("Spare-part maintenance due: %s", part.name),
                note=_(
                    "The spare part <b>%s</b> on equipment <b>%s</b> is due for maintenance. "
                    "Last maintenance date: %s.",
                    part.name,
                    equipment.display_name,
                    part.last_maintenance_date,
                ),
                user_id=responsible_user.id,
            )
            part.reminder_sent = True
