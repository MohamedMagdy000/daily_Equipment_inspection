# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    allowed_equipment_category_ids = fields.Many2many(
        comodel_name="maintenance.equipment.category",
        relation="res_users_maintenance_equipment_category_rel",
        column1="user_id",
        column2="category_id",
        string="Allowed Equipment Categories",
        help=(
            "Equipment Inspection Users can access only equipment "
            "belonging to these categories. Equipment Inspection "
            "Managers have unrestricted access."
        ),
    )

    allowed_category_ids = fields.Many2many(
        related="allowed_equipment_category_ids",
        string="Legacy Allowed Categories",
        readonly=False,
    )