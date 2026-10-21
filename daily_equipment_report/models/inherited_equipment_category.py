from odoo import api, fields, models


class MaintenanceEquipmentCategory(models.Model):
    _inherit = "maintenance.equipment.category"

    question_ids = fields.One2many(
        comodel_name="equipment.checklist.question",
        inverse_name="category_id",
        string="Inspection Questions",
        copy=True,
    )
    question_count = fields.Integer(
        string="Question Count",
        compute="_compute_question_count",
    )

    @api.depends("question_ids.active")
    def _compute_question_count(self):
        for category in self:
            category.question_count = len(category.question_ids)

    def action_view_questions(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "daily_equipment_report.action_equipment_checklist_question"
        )
        action.update({
            "domain": [("category_id", "=", self.id)],
            "context": {
                "default_category_id": self.id,
                "search_default_category_id": self.id,
            },
        })
        return action
