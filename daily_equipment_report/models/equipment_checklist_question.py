from odoo import fields, models


class EquipmentChecklistQuestion(models.Model):
    _name = "equipment.checklist.question"
    _description = "Equipment Inspection Checklist Question"
    _order = "category_id, sequence, id"

    name = fields.Char(string="Question", required=True, translate=True)
    category_id = fields.Many2one(
        comodel_name="maintenance.equipment.category",
        string="Equipment Category",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    failure_severity = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Failure Severity",
        default="medium",
        required=True,
        help=(
            "Defines the operational impact when this question is answered No. "
            "A failed inspection can be used to manually move the equipment "
            "to Out of Service."
        ),
    )
    active = fields.Boolean(default=True)

    _question_category_unique = models.Constraint(
        "unique(name, category_id)",
        "The same checklist question cannot be added twice to one category.",
    )
