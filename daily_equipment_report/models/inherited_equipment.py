from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    
    barcode = fields.Char(
        string="Barcode",
        copy=False,
        index=True,
        tracking=True,
    )

    asset_number = fields.Char(
        string="Asset Number",
        copy=False,
        index=True,
        tracking=True,
    )

    last_calibration = fields.Date(
        string="Last Calibration",
        tracking=True,
    )

    location = fields.Char(
        string="Location",
        tracking=True,
        index=True,
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        ondelete="set null",
    )


    purchase_date = fields.Date(
        string="Purchase Date",
        tracking=True,
    )

    image_1920 = fields.Image(
        string="Equipment Image",
        max_width=1920,
        max_height=1920,
    )

    operational_status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("maintenance", "Under Maintenance"),
            ("out_of_service", "Out of Service"),
        ],
        string="Operational Status",
        default="active",
        required=True,
        tracking=True,
        index=True,
    )

    spare_part_ids = fields.One2many(
        comodel_name="equipment.spare.part",
        inverse_name="equipment_id",
        string="Spare Parts",
    )

    spare_part_count = fields.Integer(
        string="Parts Count",
        compute="_compute_equipment_inspection_counts",
        store=True,
    )

    report_ids = fields.One2many(
        comodel_name="equipment.daily.report",
        inverse_name="equipment_id",
        string="Daily Inspection Reports",
    )

    report_count = fields.Integer(
        string="Reports",
        compute="_compute_equipment_inspection_counts",
        store=True,
    )

    last_report_date = fields.Datetime(
        string="Last Inspection",
        compute="_compute_last_report_date",
        store=True,
    )

    inspection_maintenance_request_count = fields.Integer(
        string="Inspection Maintenance",
        compute="_compute_inspection_maintenance_request_count",
    )

    def action_set_out_of_service(self):
        for equipment in self:
            equipment.write({
                "operational_status": "out_of_service",
            })
        return True

    def action_return_to_service(self):
        for equipment in self:
            equipment.write({
                "operational_status": "active",
            })
        return True

    @api.depends(
        "spare_part_ids",
        "report_ids",
    )
    def _compute_equipment_inspection_counts(self):
        for equipment in self:
            equipment.spare_part_count = len(
                equipment.spare_part_ids
            )

            equipment.report_count = len(
                equipment.report_ids
            )

    @api.depends("report_ids.report_date")
    def _compute_last_report_date(self):
        for equipment in self:
            dates = equipment.report_ids.mapped(
                "report_date"
            )

            equipment.last_report_date = (
                max(dates)
                if dates
                else False
            )

    @api.depends(
        "maintenance_ids.inspection_line_id",
        "maintenance_ids.state",
    )
    def _compute_inspection_maintenance_request_count(self):
        for equipment in self:
            equipment.inspection_maintenance_request_count = len(
                equipment.maintenance_ids.filtered(
                    lambda request: (
                        request.inspection_line_id
                        and request.state not in ("done", "cancelled")
                    )
                )
            )

    def action_view_reports(self):
        self.ensure_one()

        action = self.env[
            "ir.actions.actions"
        ]._for_xml_id(
            "daily_equipment_report."
            "action_equipment_daily_report"
        )

        action.update({
            "domain": [
                ("equipment_id", "=", self.id),
            ],
            "context": {
                "default_equipment_id": self.id,
                "search_default_equipment_id": self.id,
            },
        })

        return action

    def action_view_spare_parts(self):
        self.ensure_one()

        action = self.env[
            "ir.actions.actions"
        ]._for_xml_id(
            "daily_equipment_report."
            "action_equipment_spare_part"
        )

        action.update({
            "domain": [
                ("equipment_id", "=", self.id),
            ],
            "context": {
                "default_equipment_id": self.id,
                "search_default_equipment_id": self.id,
            },
        })

        return action

    def action_view_inspection_maintenance_requests(self):
        self.ensure_one()

        action = self.env[
            "ir.actions.actions"
        ]._for_xml_id(
            "maintenance.hr_equipment_request_action"
        )

        action.update({
            "domain": [
                ("equipment_id", "=", self.id),
                ("inspection_line_id", "!=", False),
            ],
            "context": {
                "default_equipment_id": self.id,
                "default_company_id": (
                    self.company_id.id
                    or self.env.company.id
                ),
                "default_maintenance_team_id": (
                    self.maintenance_team_id.id
                ),
                "search_default_from_inspection": 1,
            },
        })

        return action
