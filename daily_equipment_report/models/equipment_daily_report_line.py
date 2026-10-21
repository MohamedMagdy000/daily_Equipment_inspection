# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EquipmentDailyReportLine(models.Model):
    _name = "equipment.daily.report.line"
    _description = "Equipment Daily Inspection Report Line"
    _order = "sequence, id"

    report_id = fields.Many2one(
        comodel_name="equipment.daily.report",
        string="Report",
        required=True,
        ondelete="cascade",
        index=True,
    )

    question_id = fields.Many2one(
        comodel_name="equipment.checklist.question",
        string="Question",
        required=True,
        ondelete="restrict",
    )

    sequence = fields.Integer(
        related="question_id.sequence",
        store=True,
    )

    failure_severity = fields.Selection(
        related="question_id.failure_severity",
        string="Failure Severity",
        store=True,
        readonly=True,
    )

    answer = fields.Selection(
        selection=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        string="Answer",
    )

    issue_image = fields.Image(
        string="Issue Photo",
        max_width=1920,
        max_height=1920,
    )

    issue_description = fields.Text(
        string="Issue Description",
    )

    maintenance_request_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="inspection_line_id",
        string="Maintenance Requests",
        readonly=True,
    )

    maintenance_request_count = fields.Integer(
        string="Request Count",
        compute="_compute_maintenance_request_count",
    )

    @api.depends("maintenance_request_ids")
    def _compute_maintenance_request_count(self):
        for line in self:
            line.maintenance_request_count = len(line.maintenance_request_ids)

    @api.model_create_multi
    def create(self, vals_list):
        report_ids = [
            vals.get("report_id")
            for vals in vals_list
            if vals.get("report_id")
        ]

        reports = self.env["equipment.daily.report"].browse(report_ids)

        if any(report.state != "draft" for report in reports):
            raise UserError(
                _("Checklist lines can only be added to draft inspections.")
            )

        return super().create(vals_list)

    def write(self, vals):
        if any(line.report_id.state != "draft" for line in self):
            raise UserError(
                _("Checklist lines can only be edited in Draft status.")
            )

        return super().write(vals)

    def unlink(self):
        lines_with_requests = self.filtered("maintenance_request_ids")

        if lines_with_requests:
            raise UserError(
                _(
                    "A checklist line linked to a maintenance request cannot "
                    "be deleted. Keep it for inspection traceability."
                )
            )

        if any(line.report_id.state != "draft" for line in self):
            raise UserError(
                _("Checklist lines can only be removed in Draft status.")
            )

        return super().unlink()

    @api.constrains(
        "answer",
        "issue_image",
        "issue_description",
        "report_id",
    )
    def _check_issue_details(self):
        for line in self:
            # Draft reports may temporarily contain incomplete answers.
            if line.report_id.state == "draft":
                continue

            if line.answer == "no" and not line.issue_description:
                raise ValidationError(
                    _(
                        "An issue description is required when the answer "
                        "is No for: %s",
                        line.question_id.display_name,
                    )
                )

            if line.answer == "no" and not line.issue_image:
                raise ValidationError(
                    _(
                        "An issue photo is required when the answer "
                        "is No for: %s",
                        line.question_id.display_name,
                    )
                )

    def action_open_maintenance_request(self):
        self.ensure_one()

        requests = self.maintenance_request_ids

        if not requests:
            raise UserError(
                _("No maintenance request exists for this checklist line.")
            )

        action = self.env["ir.actions.actions"]._for_xml_id(
            "maintenance.hr_equipment_request_action"
        )

        if len(requests) == 1:
            action.update({
                "view_mode": "form",
                "res_id": requests.id,
                "views": [(False, "form")],
            })
        else:
            action.update({
                "domain": [("id", "in", requests.ids)],
            })

        return action