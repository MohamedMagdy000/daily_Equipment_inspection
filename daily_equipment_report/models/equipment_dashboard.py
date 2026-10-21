from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models


class EquipmentInspectionDashboard(models.AbstractModel):
    _name = "equipment.inspection.dashboard"
    _description = "Equipment Inspection Dashboard"

    @api.model
    def action_print_dashboard(self, filters=None):
        return self.env.ref(
            "daily_equipment_report.action_report_equipment_dashboard"
        ).report_action(
            [],
            data={"filters": filters or {}},
            config=False,
        )

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}

        Equipment = self.env["maintenance.equipment"]
        Report = self.env["equipment.daily.report"]
        Line = self.env["equipment.daily.report.line"]
        Maintenance = self.env["maintenance.request"]
        SparePart = self.env["equipment.spare.part"]

        category_id = self._to_int(filters.get("category_id"))
        equipment_id = self._to_int(filters.get("equipment_id"))
        location = (filters.get("location") or "").strip()
        severity = filters.get("severity") or False
        operational_status = filters.get("operational_status") or False

        today = fields.Date.context_today(self)

        default_from = today - timedelta(days=29)

        date_from = (
            self._to_date(filters.get("date_from"))
            or default_from
        )

        date_to = (
            self._to_date(filters.get("date_to"))
            or today
        )

        if date_from > date_to:
            date_from, date_to = date_to, date_from

        # =====================================================
        # Equipment filters
        # =====================================================

        equipment_domain = []

        if category_id:
            equipment_domain.append(
                ("category_id", "=", category_id)
            )

        if equipment_id:
            equipment_domain.append(
                ("id", "=", equipment_id)
            )

        if location:
            equipment_domain.append(
                ("location", "=", location)
            )

        if operational_status:
            equipment_domain.append(
                (
                    "operational_status",
                    "=",
                    operational_status,
                )
            )

        equipment_records = Equipment.search(
            equipment_domain
        )

        equipment_ids = equipment_records.ids


        report_domain = [
            ("equipment_id", "in", equipment_ids),
        ]

        report_domain += self._datetime_domain(
            "report_date",
            date_from,
            date_to,
        )

       

        failed_line_domain = [
            ("answer", "=", "no"),
            (
                "report_id.equipment_id",
                "in",
                equipment_ids,
            ),
        ]

        failed_line_domain += self._datetime_domain(
            "report_id.report_date",
            date_from,
            date_to,
        )

        if severity:
            failed_line_domain.append(
                (
                    "failure_severity",
                    "=",
                    severity,
                )
            )



        maintenance_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            ),
            (
                "is_inspection_generated",
                "=",
                True,
            ),
            (
                "state",
                "not in",
                ["done", "cancelled"],
            ),
        ]

        maintenance_domain += self._datetime_domain(
            "schedule_date",
            date_from,
            date_to,
        )

        if severity:
            maintenance_domain.append(
                (
                    "inspection_failure_severity",
                    "=",
                    severity,
                )
            )

        

        total_equipment = len(
            equipment_records
        )

        active_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status == "active"
            )
        )

        maintenance_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                == "maintenance"
            )
        )

        out_of_service_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                == "out_of_service"
            )
        )

        availability_rate = self._percent(
            active_equipment,
            total_equipment,
        )

        
        total_inspections = Report.search_count(
            report_domain
        )

        today_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            )
        ]

        today_domain += self._datetime_domain(
            "report_date",
            today,
            today,
        )

        inspections_today = Report.search_count(
            today_domain
        )

        draft_inspections = Report.search_count(
            report_domain
            + [
                ("state", "=", "draft"),
            ]
        )

        submitted_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "submitted",
                    )
                ]
            )
        )

        approved_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "approved",
                    )
                ]
            )
        )

        closed_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "closed",
                    )
                ]
            )
        )

        failed_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "has_issue",
                        "=",
                        True,
                    )
                ]
            )
        )

        critical_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "has_critical_issue",
                        "=",
                        True,
                    )
                ]
            )
        )

        completed_domain = (
            report_domain
            + [
                (
                    "state",
                    "in",
                    [
                        "submitted",
                        "approved",
                        "closed",
                    ],
                )
            ]
        )

        completed_inspections = (
            Report.search_count(
                completed_domain
            )
        )

        passed_completed = (
            Report.search_count(
                completed_domain
                + [
                    (
                        "has_issue",
                        "=",
                        False,
                    )
                ]
            )
        )

        pass_rate = self._percent(
            passed_completed,
            completed_inspections,
        )



        open_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "state",
                        "not in",
                        ["done", "cancelled"],
                    )
                ]
            )
        )

        completed_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "state",
                        "=",
                        "done",
                    )
                ]
            )
        )

        critical_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "inspection_failure_severity",
                        "=",
                        "critical",
                    )
                ]
            )
        )

        in_progress_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "state",
                        "=",
                        "normal",
                    ),
                ]
            )
        )


        spare_part_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            ),
            (
                "active",
                "=",
                True,
            ),
        ]

        spare_parts = SparePart.search(
            spare_part_domain
        )

        warning_date = (
            today
            + timedelta(days=7)
        )

        overdue_parts = (
            spare_parts.filtered(
                lambda part:
                part.next_maintenance_date
                and
                part.next_maintenance_date
                < today
            )
        )

        due_soon_parts = (
            spare_parts.filtered(
                lambda part:
                part.next_maintenance_date
                and
                today
                <= part.next_maintenance_date
                <= warning_date
            )
        )

        healthy_parts = (
            spare_parts
            - overdue_parts
            - due_soon_parts
        )


        severity_counts = (
            self._severity_counts(
                failed_line_domain,
                Line,
            )
        )

        top_defects = (
            self._top_defects(
                failed_line_domain,
                Line,
            )
        )

        category_failures = (
            self._category_failures(
                report_domain,
                Report,
            )
        )

        location_failures = (
            self._location_failures(
                report_domain,
                Report,
            )
        )

        inspection_trend = (
            self._inspection_trend(
                report_domain,
                Report,
                date_from,
                date_to,
            )
        )



        recent_critical = (
            self._recent_critical(
                report_domain,
                Report,
            )
        )

        equipment_attention = (
            self._equipment_attention(
                equipment_records
            )
        )

        overdue_parts_rows = (
            self._overdue_parts_rows(
                overdue_parts,
                today,
            )
        )

        recent_maintenance = (
            self._recent_maintenance(
                maintenance_domain,
                Maintenance,
            )
        )

        return {

            "filters": {
                "date_from":
                    fields.Date.to_string(
                        date_from
                    ),

                "date_to":
                    fields.Date.to_string(
                        date_to
                    ),

                "category_id":
                    category_id or False,

                "equipment_id":
                    equipment_id or False,

                "location":
                    location or False,

                "severity":
                    severity or False,

                "operational_status":
                    operational_status
                    or False,
            },

            "filter_options":
                self._get_filter_options(),

            "alerts": {
                "critical_inspections":
                    critical_inspections,

                "open_maintenance":
                    open_maintenance,

                "out_of_service":
                    out_of_service_equipment,

                "overdue_parts":
                    len(overdue_parts),

                "pending_approval":
                    submitted_inspections,
            },

            "equipment": {
                "total":
                    total_equipment,

                "active":
                    active_equipment,

                "maintenance":
                    maintenance_equipment,

                "out_of_service":
                    out_of_service_equipment,

                "availability_rate":
                    availability_rate,
            },

            "inspections": {
                "total":
                    total_inspections,

                "today":
                    inspections_today,

                "draft":
                    draft_inspections,

                "submitted":
                    submitted_inspections,

                "approved":
                    approved_inspections,

                "closed":
                    closed_inspections,

                "failed":
                    failed_inspections,

                "critical":
                    critical_inspections,

                "pass_rate":
                    pass_rate,
            },

            "maintenance": {
                "open":
                    open_maintenance,

                "in_progress":
                    in_progress_maintenance,

                "critical":
                    critical_maintenance,

                "completed":
                    completed_maintenance,
            },

            "spare_parts": {
                "total":
                    len(spare_parts),

                "healthy":
                    len(healthy_parts),

                "due_soon":
                    len(due_soon_parts),

                "overdue":
                    len(overdue_parts),
            },

            "analytics": {
                "severity":
                    severity_counts,

                "top_defects":
                    top_defects,

                "category_failures":
                    category_failures,

                "location_failures":
                    location_failures,

                "inspection_trend":
                    inspection_trend,
            },

            "details": {
                "recent_critical":
                    recent_critical,

                "equipment_attention":
                    equipment_attention,

                "overdue_parts":
                    overdue_parts_rows,

                "recent_maintenance":
                    recent_maintenance,
            },
        }


    @api.model
    def action_open_equipment(
        self,
        equipment_id,
    ):
        equipment = (
            self.env[
                "maintenance.equipment"
            ]
            .browse(
                int(equipment_id)
            )
            .exists()
        )

        if not equipment:
            return False

        
        view = self.env.ref(
            "daily_equipment_report."
            "view_daily_inspection_equipment_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                equipment.display_name,

            "res_model":
                "maintenance.equipment",

            "res_id":
                equipment.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    @api.model
    def action_open_inspection(
        self,
        inspection_id,
    ):
        report = (
            self.env[
                "equipment.daily.report"
            ]
            .browse(
                int(inspection_id)
            )
            .exists()
        )

        if not report:
            return False

        view = self.env.ref(
            "daily_equipment_report."
            "view_equipment_daily_report_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                report.display_name,

            "res_model":
                "equipment.daily.report",

            "res_id":
                report.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    @api.model
    def action_open_maintenance_request(
        self,
        request_id,
    ):
        request = (
            self.env[
                "maintenance.request"
            ]
            .browse(
                int(request_id)
            )
            .exists()
        )

        if not request:
            return False

        view = self.env.ref(
            "maintenance."
            "hr_equipment_request_view_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                request.display_name,

            "res_model":
                "maintenance.request",

            "res_id":
                request.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    @api.model
    def action_open_equipment_list(self, filters=None, status=False):
        """Open the custom Equipment list using the current dashboard filters."""
        filters = filters or {}

        domain = []

        category_id = self._to_int(filters.get("category_id"))
        equipment_id = self._to_int(filters.get("equipment_id"))
        location = (filters.get("location") or "").strip()

        if category_id:
            domain.append(("category_id", "=", category_id))

        if equipment_id:
            domain.append(("id", "=", equipment_id))

        if location:
            domain.append(("location", "=", location))

        effective_status = status or filters.get("operational_status") or False
        if effective_status:
            domain.append(("operational_status", "=", effective_status))

        list_view = self.env.ref(
            "daily_equipment_report.view_daily_inspection_equipment_list"
        )
        form_view = self.env.ref(
            "daily_equipment_report.view_daily_inspection_equipment_form"
        )
        search_view = self.env.ref(
            "daily_equipment_report.view_daily_inspection_equipment_search"
        )

        names = {
            "active": "Active Equipment",
            "maintenance": "Equipment Under Maintenance",
            "out_of_service": "Out of Service Equipment",
        }

        return {
            "type": "ir.actions.act_window",
            "name": names.get(effective_status, "Equipment"),
            "res_model": "maintenance.equipment",
            "view_mode": "list,form",
            "views": [
                (list_view.id, "list"),
                (form_view.id, "form"),
            ],
            "search_view_id": [search_view.id, search_view.name],
            "domain": domain,
            "context": {},
            "target": "current",
        }

    @api.model
    def action_open_severity_inspections(
        self,
        filters=None,
        severity=False,
        question_id=False,
        selected_equipment_id=False,
    ):
        """Open inspections matching the selected failure criteria."""
        filters = filters or {}
        severity = severity or filters.get("severity") or False

        Equipment = self.env["maintenance.equipment"]
        Line = self.env["equipment.daily.report.line"]

        equipment_domain = []

        category_id = self._to_int(filters.get("category_id"))
        equipment_id = self._to_int(filters.get("equipment_id"))
        question_id = self._to_int(question_id)
        selected_equipment_id = self._to_int(selected_equipment_id)
        location = (filters.get("location") or "").strip()
        operational_status = filters.get("operational_status") or False

        if selected_equipment_id:
            equipment_id = selected_equipment_id

        if category_id:
            equipment_domain.append(("category_id", "=", category_id))
        if equipment_id:
            equipment_domain.append(("id", "=", equipment_id))
        if location:
            equipment_domain.append(("location", "=", location))
        if operational_status:
            equipment_domain.append(("operational_status", "=", operational_status))

        equipment_ids = Equipment.search(equipment_domain).ids

        today = fields.Date.context_today(self)
        date_from = self._to_date(filters.get("date_from")) or (today - timedelta(days=29))
        date_to = self._to_date(filters.get("date_to")) or today
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        line_domain = [
            ("answer", "=", "no"),
            ("report_id.equipment_id", "in", equipment_ids),
        ]
        line_domain += self._datetime_domain(
            "report_id.report_date",
            date_from,
            date_to,
        )
        if severity:
            line_domain.append(("failure_severity", "=", severity))
        if question_id:
            line_domain.append(("question_id", "=", question_id))

        report_ids = list(set(Line.search(line_domain).mapped("report_id").ids))

        list_view = self.env.ref(
            "daily_equipment_report.view_equipment_daily_report_list"
        )
        form_view = self.env.ref(
            "daily_equipment_report.view_equipment_daily_report_form"
        )

        labels = {
            "low": "Low Severity Inspections",
            "medium": "Medium Severity Inspections",
            "high": "High Severity Inspections",
            "critical": "Critical Severity Inspections",
        }
        if question_id and selected_equipment_id:
            question = self.env["equipment.checklist.question"].browse(
                question_id
            ).exists()
            equipment = Equipment.browse(selected_equipment_id).exists()
            action_name = "%s - %s: Failed Inspections" % (
                question.display_name if question else "Checklist Question",
                equipment.display_name if equipment else "Equipment",
            )
        else:
            action_name = labels.get(severity, "Failed Inspections")

        return {
            "type": "ir.actions.act_window",
            "name": action_name,
            "res_model": "equipment.daily.report",
            "view_mode": "list,form",
            "views": [
                (list_view.id, "list"),
                (form_view.id, "form"),
            ],
            "domain": [("id", "in", report_ids)],
            "context": {},
            "target": "current",
        }

   

    @api.model
    def _get_filter_options(self):

        Equipment = self.env[
            "maintenance.equipment"
        ]

        Category = self.env[
            "maintenance.equipment.category"
        ]

        equipments = Equipment.search(
            [],
            order="name, id",
        )

        categories = Category.search(
            [],
            order="name, id",
        )

        locations = sorted(
            {
                rec.location.strip()
                for rec in equipments
                if rec.location
                and rec.location.strip()
            }
        )

        return {

            "categories": [
                {
                    "id":
                        rec.id,

                    "name":
                        rec.display_name,
                }
                for rec in categories
            ],

            "equipments": [
                {
                    "id":
                        rec.id,

                    "name":
                        rec.display_name,

                    "category_id":
                        rec.category_id.id
                        or False,

                    "location":
                        rec.location or "",
                }
                for rec in equipments
            ],

            "locations":
                locations,

            "severities": [
                {
                    "value": "low",
                    "label": "Low",
                },
                {
                    "value": "medium",
                    "label": "Medium",
                },
                {
                    "value": "high",
                    "label": "High",
                },
                {
                    "value": "critical",
                    "label": "Critical",
                },
            ],

            "operational_statuses": [
                {
                    "value":
                        "active",

                    "label":
                        "Active",
                },
                {
                    "value":
                        "maintenance",

                    "label":
                        "Under Maintenance",
                },
                {
                    "value":
                        "out_of_service",

                    "label":
                        "Out of Service",
                },
            ],
        }

 

    @api.model
    def _severity_counts(
        self,
        domain,
        Line,
    ):

        result = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }

        grouped = Line._read_group(
            domain,
            [
                "failure_severity",
            ],
            [
                "__count",
            ],
        )

        for severity, count in grouped:

            if severity in result:
                result[
                    severity
                ] = count

        result["total"] = sum(
            result.values()
        )

        return result

   
    @api.model
    def _top_defects(
        self,
        domain,
        Line,
    ):

        rows = []

        grouped = Line._read_group(
            domain,
            [
                "question_id",
            ],
            [
                "__count",
            ],
            order="__count desc",
            limit=10,
        )

        questions = [
            question
            for question, _count in grouped
            if question
        ]
        equipment_counts = defaultdict(dict)

        if questions:
            equipment_grouped = Line._read_group(
                domain
                + [
                    (
                        "question_id",
                        "in",
                        [question.id for question in questions],
                    )
                ],
                [
                    "question_id",
                    "report_id",
                ],
                [
                    "__count",
                ],
            )

            for question, report, count in equipment_grouped:
                if question and report and report.equipment_id:
                    equipment = report.equipment_id
                    item = equipment_counts[question.id].setdefault(
                        equipment.id,
                        {
                            "id": equipment.id,
                            "name": equipment.display_name,
                            "count": 0,
                        },
                    )
                    item["count"] += count

        for question, count in grouped:

            if question:

                rows.append({
                    "id":
                        question.id,

                    "name":
                        question.display_name,

                    "count":
                        count,

                    "equipment":
                        sorted(
                            equipment_counts[question.id].values(),
                            key=lambda item: (
                                -item["count"],
                                item["name"].lower(),
                            ),
                        ),
                })

        return rows

    # =========================================================
    # Failures by category
    # =========================================================

    @api.model
    def _category_failures(
        self,
        report_domain,
        Report,
    ):

        rows = []

        grouped = Report._read_group(

            report_domain
            + [
                (
                    "has_issue",
                    "=",
                    True,
                )
            ],

            [
                "category_id",
            ],

            [
                "__count",
            ],

            order="__count desc",

            limit=10,
        )

        for category, count in grouped:

            if category:

                rows.append({
                    "id":
                        category.id,

                    "name":
                        category.display_name,

                    "count":
                        count,
                })

        return rows

    # =========================================================
    # Failures by location
    # =========================================================

    @api.model
    def _location_failures(
        self,
        report_domain,
        Report,
    ):

        counts = defaultdict(int)

        grouped = Report._read_group(

            report_domain
            + [
                (
                    "has_issue",
                    "=",
                    True,
                )
            ],

            [
                "equipment_id",
            ],

            [
                "__count",
            ],
        )

        for equipment, count in grouped:

            location = (
                equipment.location
                or "Unspecified"
            ).strip()

            if not location:
                location = "Unspecified"

            counts[
                location
            ] += count

        sorted_rows = sorted(
            counts.items(),
            key=lambda item:
                item[1],
            reverse=True,
        )

        return [
            {
                "name":
                    location,

                "count":
                    count,
            }
            for location, count
            in sorted_rows[:10]
        ]


    @api.model
    def _inspection_trend(
        self,
        report_domain,
        Report,
        date_from,
        date_to,
    ):

        counts = defaultdict(int)

        reports = Report.search(
            report_domain
        )

        for report in reports:

            if report.report_date:

                local_dt = (
                    fields.Datetime
                    .context_timestamp(
                        report,
                        report.report_date,
                    )
                )

                counts[
                    local_dt.date()
                ] += 1

        total_days = (
            date_to
            - date_from
        ).days + 1

        if total_days <= 14:

            step = 1

        elif total_days <= 60:

            step = 7

        else:

            step = 30

        points = []

        cursor = date_from

        while cursor <= date_to:

            bucket_end = min(
                cursor
                + timedelta(
                    days=step - 1
                ),
                date_to,
            )

            bucket_days = (
                bucket_end
                - cursor
            ).days + 1

            count = sum(
                counts.get(
                    cursor
                    + timedelta(
                        days=offset
                    ),
                    0,
                )
                for offset
                in range(bucket_days)
            )

            label = (
                cursor.strftime(
                    "%d %b"
                )
            )

            points.append({
                "label":
                    label,

                "count":
                    count,
            })

            cursor = (
                bucket_end
                + timedelta(days=1)
            )

        return points[-18:]

   

    @api.model
    def _recent_critical(
        self,
        report_domain,
        Report,
    ):

        reports = Report.search(

            report_domain
            + [
                (
                    "has_critical_issue",
                    "=",
                    True,
                )
            ],

            order=(
                "report_date desc, "
                "id desc"
            ),

            limit=10,
        )

        rows = []

        for report in reports:

            critical_lines = (
                report.line_ids.filtered(
                    lambda line:
                    line.answer == "no"
                    and
                    line.failure_severity
                    == "critical"
                )
            )

            defects = ", ".join(
                critical_lines
                .mapped(
                    "question_id.name"
                )[:3]
            )

            rows.append({

                "id":
                    report.id,

                "name":
                    report.display_name,

                "equipment":
                    report
                    .equipment_id
                    .display_name,

                "category":
                    report
                    .category_id
                    .display_name
                    or "",

                "location":
                    report
                    .equipment_id
                    .location
                    or "",

                "defects":
                    defects,

                "inspector":
                    report
                    .user_id
                    .display_name,

                "date":
                    self._format_datetime(
                        report.report_date,
                        report,
                    ),

                "state":
                    report.state,
            })

        return rows

   

    @api.model
    def _equipment_attention(
        self,
        equipment_records,
    ):

        records = (
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                in (
                    "maintenance",
                    "out_of_service",
                )
            )
        )

        records = records.sorted(
            key=lambda rec: (
                rec.operational_status
                != "out_of_service",

                rec.name or "",
            )
        )[:10]

        return [

            {
                "id":
                    rec.id,

                "name":
                    rec.display_name,

                "category":
                    rec
                    .category_id
                    .display_name
                    or "",

                "location":
                    rec.location or "",

                "status":
                    rec.operational_status,

                "last_inspection":
                    self._format_datetime(
                        rec.last_report_date,
                        rec,
                    ),

                "open_maintenance":
                    rec.maintenance_open_count,
            }

            for rec in records
        ]

   

    @api.model
    def _overdue_parts_rows(
        self,
        overdue_parts,
        today,
    ):

        parts = overdue_parts.sorted(
            key=lambda part:
                part.next_maintenance_date
                or today
        )[:10]

        return [

            {
                "id":
                    part.id,

                "name":
                    part.display_name,

                "equipment":
                    part
                    .equipment_id
                    .display_name,

                "category":
                    part
                    .category_id
                    .display_name
                    or "",

                "last_date":
                    (
                        fields.Date
                        .to_string(
                            part
                            .last_maintenance_date
                        )
                        if
                        part.last_maintenance_date
                        else ""
                    ),

                "next_date":
                    (
                        fields.Date
                        .to_string(
                            part
                            .next_maintenance_date
                        )
                        if
                        part.next_maintenance_date
                        else ""
                    ),

                "days_overdue":
                    (
                        today
                        - part
                        .next_maintenance_date
                    ).days
                    if
                    part.next_maintenance_date
                    else 0,
            }

            for part in parts
        ]

    # =========================================================
    # Maintenance table
    # =========================================================

    @api.model
    def _recent_maintenance(
        self,
        maintenance_domain,
        Maintenance,
    ):

        requests = Maintenance.search(
            maintenance_domain,
            order=(
                "schedule_date desc, "
                "id desc"
            ),
            limit=10,
        )

        return [

            {
                "id":
                    req.id,

                "name":
                    req.display_name,

                "equipment":
                    (
                        req
                        .equipment_id
                        .display_name
                        if req.equipment_id
                        else ""
                    ),

                "inspection":
                    (
                        req
                        .inspection_report_id
                        .display_name
                        if
                        req.inspection_report_id
                        else ""
                    ),

                "severity":
                    (
                        req
                        .inspection_failure_severity
                        or ""
                    ),

                "stage":
                    (
                        req
                        .stage_id
                        .display_name
                        or ""
                    ),

                "technician":
                    (
                        req
                        .user_ids
                        .display_name
                        if req.user_ids
                        else "Unassigned"
                    ),

                "priority":
                    req.priority or "0",
            }

            for req in requests
        ]

    
    @staticmethod
    def _to_int(value):

        try:

            return (
                int(value)
                if value
                not in (
                    None,
                    False,
                    "",
                    0,
                    "0",
                )
                else False
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    @staticmethod
    def _to_date(value):

        if not value:
            return False

        try:

            return fields.Date.to_date(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    @staticmethod
    def _percent(
        numerator,
        denominator,
    ):

        if not denominator:
            return 0.0

        return round(
            (
                numerator
                / denominator
            )
            * 100,
            1,
        )

    @staticmethod
    def _datetime_domain(
        field_name,
        date_from,
        date_to,
    ):

        start_dt = datetime.combine(
            date_from,
            time.min,
        )

        end_dt = datetime.combine(
            date_to
            + timedelta(days=1),
            time.min,
        )

        return [
            (
                field_name,
                ">=",
                fields.Datetime
                .to_string(
                    start_dt
                ),
            ),
            (
                field_name,
                "<",
                fields.Datetime
                .to_string(
                    end_dt
                ),
            ),
        ]

    @staticmethod
    def _date_domain(
        field_name,
        date_from,
        date_to,
    ):

        return [
            (
                field_name,
                ">=",
                fields.Date.to_string(
                    date_from
                ),
            ),
            (
                field_name,
                "<=",
                fields.Date.to_string(
                    date_to
                ),
            ),
        ]

    @staticmethod
    def _format_datetime(
        value,
        record,
    ):

        if not value:
            return ""

        local_dt = (
            fields.Datetime
            .context_timestamp(
                record,
                value,
            )
        )

        return local_dt.strftime(
            "%Y-%m-%d %H:%M"
        )
