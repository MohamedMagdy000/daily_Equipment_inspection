from datetime import timedelta
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command


class EquipmentDailyReport(models.Model):
    _name = "equipment.daily.report"
    _description = "Equipment Daily Inspection Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "report_date desc, id desc"
    _rec_name = "name"
    _check_company_auto = True

    name = fields.Char(
        string="Report Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
    )

    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        string="Equipment",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        domain="[('active', '=', True)]",
    )

    category_id = fields.Many2one(
        comodel_name="maintenance.equipment.category",
        related="equipment_id.category_id",
        string="Equipment Category",
        store=True,
        readonly=True,
        index=True,
    )

    equipment_operational_status = fields.Selection(
        related="equipment_id.operational_status",
        string="Equipment Status",
        readonly=True,
    )

    company_id = fields.Many2one(
        related="equipment_id.company_id",
        store=True,
        readonly=True,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Inspected By",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )

    report_date = fields.Datetime(
        string="Inspection Date & Time",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        tracking=True,
        index=True,
    )

    submitted_date = fields.Datetime(
        string="Submitted On",
        readonly=True,
        copy=False,
    )

    approved_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Approved By",
        readonly=True,
        copy=False,
        tracking=True,
    )

    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
        copy=False,
    )

    closed_date = fields.Datetime(
        string="Closed On",
        readonly=True,
        copy=False,
    )

    line_ids = fields.One2many(
        comodel_name="equipment.daily.report.line",
        inverse_name="report_id",
        string="Inspection Checklist",
        copy=False,
    )

    has_issue = fields.Boolean(
        string="Has Issue",
        compute="_compute_issue_flags",
        store=True,
        index=True,
    )

    has_critical_issue = fields.Boolean(
        string="Critical Issue",
        compute="_compute_issue_flags",
        store=True,
        index=True,
    )

    maintenance_request_count = fields.Integer(
        string="Maintenance Requests",
        compute="_compute_maintenance_request_count",
    )

    @api.depends(
        "line_ids.answer",
        "line_ids.question_id.failure_severity",
    )
    def _compute_issue_flags(self):
        for report in self:
            failed_lines = report.line_ids.filtered(
                lambda line: line.answer == "no"
            )

            report.has_issue = bool(failed_lines)

            report.has_critical_issue = any(
                line.failure_severity == "critical"
                for line in failed_lines
            )

    @api.depends("line_ids.maintenance_request_ids")
    def _compute_maintenance_request_count(self):
        for report in self:
            report.maintenance_request_count = sum(
                report.line_ids.mapped("maintenance_request_count")
            )

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        for report in self:
            if report.equipment_id:
                report.line_ids = report._prepare_checklist_commands(
                    report.equipment_id
                )
            else:
                report.line_ids = [Command.clear()]

    def _prepare_checklist_commands(self, equipment):
        commands = [Command.clear()]

        questions = (
            equipment.category_id.question_ids
            .filtered("active")
            .sorted(key=lambda question: (question.sequence, question.id))
        )

        for question in questions:
            values = {
                "question_id": question.id,
            }

            commands.append(
                Command.create(values)
            )

        return commands

    def _check_daily_restriction(
        self,
        equipment,
        report_date=None,
    ):
        report_date = report_date or fields.Datetime.now()

        last_report = self.search(
            [
                ("equipment_id", "=", equipment.id),
            ],
            order="report_date desc, id desc",
            limit=1,
        )

        if (
            last_report
            and report_date - last_report.report_date
            < timedelta(hours=24)
        ):
            next_allowed = (
                last_report.report_date
                + timedelta(hours=24)
            )

            raise UserError(
                _(
                    "A daily inspection already exists for %s. "
                    "The next inspection can be created after %s.",
                    equipment.display_name,
                    fields.Datetime.to_string(next_allowed),
                )
            )

    def _validate_submission(self):
        for report in self:
            if not report.line_ids:
                raise ValidationError(
                    _(
                        "The inspection checklist is empty. Configure "
                        "active questions on the equipment category "
                        "before submitting this report."
                    )
                )

            expected_question_ids = set(
                report.equipment_id.category_id.question_ids
                .filtered("active")
                .ids
            )

            actual_question_ids = set(
                report.line_ids.mapped("question_id").ids
            )

            if expected_question_ids != actual_question_ids:
                raise ValidationError(
                    _(
                        "The inspection checklist must contain every "
                        "active question configured for the equipment "
                        "category."
                    )
                )

            unanswered_lines = report.line_ids.filtered(
                lambda line: not line.answer
            )

            if unanswered_lines:
                raise ValidationError(
                    _(
                        "Answer every checklist question before "
                        "submitting the inspection."
                    )
                )

            invalid_failure_lines = report.line_ids.filtered(
                lambda line: (
                    line.answer == "no"
                    and (
                        not line.issue_description
                        or not line.issue_image
                    )
                )
            )

            if invalid_failure_lines:
                question_names = ", ".join(
                    invalid_failure_lines.mapped(
                        "question_id.name"
                    )
                )

                raise ValidationError(
                    _(
                        "A photo and issue description are required "
                        "for every failed check. Missing details for: %s",
                        question_names,
                    )
                )

    def _get_maintenance_team(self):
        self.ensure_one()

        equipment = self.equipment_id
        company = self.company_id or self.env.company

        maintenance_team = equipment.maintenance_team_id

        if not maintenance_team:
            maintenance_team = self.env[
                "maintenance.team"
            ].search(
                [
                    "|",
                    ("company_id", "=", company.id),
                    ("company_id", "=", False),
                ],
                order="company_id desc, id",
                limit=1,
            )

        if not maintenance_team:
            raise ValidationError(
                _(
                    "No Maintenance Team is configured. Create at "
                    "least one Maintenance Team before submitting "
                    "an inspection containing failed checks."
                )
            )

        return maintenance_team

    def _prepare_maintenance_request_values(
            self,
            inspection_line,
            maintenance_team,
    ):
        self.ensure_one()

        priority_by_severity = {
            "low": "1",
            "medium": "2",
            "high": "3",
            "critical": "3",
        }

        severity_label = inspection_line._fields[
            "failure_severity"
        ].get_description(
            self.env,
            inspection_line.failure_severity,
        )

        description = Markup(
            """
            <p>
                <strong>
                    Automatically generated from a failed equipment inspection.
                </strong>
            </p>
            <ul>
                <li><strong>Inspection:</strong> {inspection}</li>
                <li><strong>Equipment:</strong> {equipment}</li>
                <li><strong>Question:</strong> {question}</li>
                <li><strong>Severity:</strong> {severity}</li>
                <li><strong>Inspector:</strong> {inspector}</li>
            </ul>
            <p>
                <strong>Issue description:</strong><br/>
                {issue_description}
            </p>
            """
        ).format(
            inspection=self.display_name,
            equipment=self.equipment_id.display_name,
            question=inspection_line.question_id.display_name,
            severity=severity_label,
            inspector=self.user_id.display_name,
            issue_description=inspection_line.issue_description or "",
        )

        return {
            "name": _(
                "%s failed - %s",
                inspection_line.question_id.name,
                self.equipment_id.display_name,
            ),
            "description": description,
            "company_id": self.company_id.id or self.env.company.id,
            "equipment_id": self.equipment_id.id,
            "maintenance_type": "corrective",
            "maintenance_team_id": maintenance_team.id,
            "owner_user_id": self.user_id.id,
            "priority": priority_by_severity.get(
                inspection_line.failure_severity,
                "2",
            ),
            "inspection_line_id": inspection_line.id,
        }

    def _create_maintenance_requests(self):
        MaintenanceRequest = self.env[
            "maintenance.request"
        ]

        for report in self:
            failed_lines = report.line_ids.filtered(
                lambda line: line.answer == "no"
            )

            if not failed_lines:
                continue

            maintenance_team = report._get_maintenance_team()
            created_requests = self.env[
                "maintenance.request"
            ]

            for line in failed_lines:
                if line.maintenance_request_ids:
                    continue

                values = (
                    report._prepare_maintenance_request_values(
                        line,
                        maintenance_team,
                    )
                )

                request = MaintenanceRequest.create(values)
                created_requests |= request

                request.message_post(
                    body=_(
                        "This corrective maintenance request was "
                        "created automatically from inspection %s.",
                        report._get_html_link(),
                    )
                )

            if created_requests:
                report.message_post(
                    body=_(
                        "%s corrective maintenance request(s) "
                        "were created automatically.",
                        len(created_requests),
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        Equipment = self.env["maintenance.equipment"]
        sequence = self.env["ir.sequence"]

        for values in vals_list:
            equipment = Equipment.browse(
                values.get("equipment_id")
            ).exists()

            if not equipment:
                continue

            report_date = fields.Datetime.to_datetime(
                values.get("report_date")
                or fields.Datetime.now()
            )

            self._check_daily_restriction(
                equipment,
                report_date,
            )

            if (
                not values.get("name")
                or values.get("name") == _("New")
            ):
                values["name"] = (
                    sequence.next_by_code(
                        "equipment.daily.report"
                    )
                    or _("New")
                )

            line_commands = values.get("line_ids") or []
            create_command_indexes = [
                index
                for index, command in enumerate(line_commands)
                if command[0] == Command.CREATE
            ]

            if not create_command_indexes:
                values["line_ids"] = (
                    self._prepare_checklist_commands(equipment)
                )
                continue

            question_ids = (
                equipment.category_id.question_ids
                .filtered("active")
                .sorted(key=lambda question: (question.sequence, question.id))
                .ids
            )
            explicitly_selected_ids = {
                line_commands[index][2].get("question_id")
                for index in create_command_indexes
                if line_commands[index][2].get("question_id")
            }
            available_question_ids = iter(
                question_id
                for question_id in question_ids
                if question_id not in explicitly_selected_ids
            )

            for index in create_command_indexes:
                command = line_commands[index]
                line_values = dict(command[2])
                if not line_values.get("question_id"):
                    try:
                        line_values["question_id"] = next(
                            available_question_ids
                        )
                    except StopIteration as error:
                        raise ValidationError(
                            _(
                                "The submitted checklist contains more "
                                "lines than the active questions for this "
                                "equipment category."
                            )
                        ) from error
                    line_commands[index] = Command.create(line_values)

            values["line_ids"] = line_commands

        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get(
            "skip_inspection_workflow_lock"
        ):
            return super().write(vals)

        if "state" in vals:
            raise UserError(
                _(
                    "Use the workflow buttons to change "
                    "the inspection status."
                )
            )

        protected_fields = {
            "equipment_id",
            "user_id",
            "report_date",
            "line_ids",
        }

        if protected_fields.intersection(vals):
            locked_reports = self.filtered(
                lambda report: report.state != "draft"
            )

            if locked_reports:
                raise UserError(
                    _(
                        "Submitted, approved, or closed inspections "
                        "cannot be edited. Reset the report to Draft "
                        "first."
                    )
                )

        return super().write(vals)

    def unlink(self):
        non_draft_reports = self.filtered(
            lambda report: report.state != "draft"
        )

        if non_draft_reports:
            raise UserError(
                _("Only draft inspections can be deleted.")
            )

        linked_requests = self.mapped(
            "line_ids.maintenance_request_ids"
        )

        if linked_requests:
            raise UserError(
                _(
                    "An inspection linked to maintenance requests "
                    "cannot be deleted. Keep it for audit and "
                    "maintenance traceability."
                )
            )

        return super().unlink()

    def action_submit(self):
        for report in self:
            if report.state != "draft":
                raise UserError(
                    _(
                        "Only draft inspections can be submitted."
                    )
                )

            report._validate_submission()

            
            report._create_maintenance_requests()

            report.with_context(
                skip_inspection_workflow_lock=True
            ).write({
                "state": "submitted",
                "submitted_date": fields.Datetime.now(),
            })

        return True

    def action_approve(self):
        if not self.env.user.has_group(
            "daily_equipment_report."
            "group_equipment_manager"
        ):
            raise AccessError(
                _(
                    "Only Equipment Inspection Managers "
                    "can approve reports."
                )
            )

        for report in self:
            if report.state != "submitted":
                raise UserError(
                    _(
                        "Only submitted inspections "
                        "can be approved."
                    )
                )

            report.with_context(
                skip_inspection_workflow_lock=True
            ).write({
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })

        return True

    def action_set_equipment_out_of_service(self):
        if not self.env.user.has_group(
            "daily_equipment_report."
            "group_equipment_manager"
        ):
            raise AccessError(
                _(
                    "Only Equipment Inspection Managers "
                    "can change equipment service status."
                )
            )

        for report in self:
            if report.state != "submitted":
                raise UserError(
                    _(
                        "Only submitted inspections can move "
                        "equipment Out of Service."
                    )
                )

            if not report.line_ids.filtered(
                lambda line: line.answer == "no"
            ):
                raise UserError(
                    _(
                        "Equipment can only be moved Out of Service "
                        "when the inspection contains a failed check."
                    )
                )

            report.with_context(
                skip_inspection_workflow_lock=True
            ).write({
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })

            report.equipment_id.write({
                "operational_status": "out_of_service",
            })
            report.message_post(
                body=_(
                    "The inspection was approved and the equipment "
                    "was moved to Out of Service because the inspection "
                    "contains a failed check."
                )
            )

        return {
            "type": "ir.actions.client",
            "tag": "soft_reload",
        }

    def action_close(self):
        if not self.env.user.has_group(
            "daily_equipment_report."
            "group_equipment_manager"
        ):
            raise AccessError(
                _(
                    "Only Equipment Inspection Managers "
                    "can close reports."
                )
            )

        for report in self:
            if report.state != "approved":
                raise UserError(
                    _(
                        "Only approved inspections "
                        "can be closed."
                    )
                )

            report.with_context(
                skip_inspection_workflow_lock=True
            ).write({
                "state": "closed",
                "closed_date": fields.Datetime.now(),
            })

        return True

    def action_reset_to_draft(self):
        if not self.env.user.has_group(
            "daily_equipment_report."
            "group_equipment_manager"
        ):
            raise AccessError(
                _(
                    "Only Equipment Inspection Managers "
                    "can reset reports."
                )
            )

        self.with_context(
            skip_inspection_workflow_lock=True
        ).write({
            "state": "draft",
            "submitted_date": False,
            "approved_by_id": False,
            "approved_date": False,
            "closed_date": False,
        })

        self.message_post(
            body=_(
                "The inspection was reset to Draft. Existing "
                "maintenance requests were retained for audit "
                "traceability and will not be duplicated when "
                "the report is submitted again."
            )
        )

        return True

    def action_view_maintenance_requests(self):
        self.ensure_one()

        action = self.env[
            "ir.actions.actions"
        ]._for_xml_id(
            "maintenance.hr_equipment_request_action"
        )

        action.update({
            "domain": [
                ("inspection_report_id", "=", self.id),
            ],
            "context": {
                "default_equipment_id": self.equipment_id.id,
                "default_inspection_report_id": self.id,
                "search_default_from_inspection": 1,
            },
        })

        return action
