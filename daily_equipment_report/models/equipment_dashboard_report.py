from odoo import api, fields, models


class EquipmentDashboardReport(models.AbstractModel):
    _name = "report.daily_equipment_report.report_equipment_dashboard"
    _description = "Equipment Dashboard PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        filters = (data or {}).get("filters") or {}
        dashboard = self.env["equipment.inspection.dashboard"]
        result = dashboard.get_dashboard_data(filters)
        applied_filters = result["filters"]
        options = result["filter_options"]

        def selected_label(option_list, value):
            return next(
                (
                    option["name"]
                    for option in option_list
                    if option["id"] == value
                ),
                "",
            )

        filter_labels = []
        if applied_filters["category_id"]:
            filter_labels.append(
                (
                    "Category",
                    selected_label(
                        options["categories"],
                        applied_filters["category_id"],
                    ),
                )
            )
        if applied_filters["equipment_id"]:
            filter_labels.append(
                (
                    "Equipment",
                    selected_label(
                        options["equipments"],
                        applied_filters["equipment_id"],
                    ),
                )
            )
        if applied_filters["location"]:
            filter_labels.append(
                ("Location", applied_filters["location"])
            )
        if applied_filters["severity"]:
            filter_labels.append(
                (
                    "Severity",
                    next(
                        (
                            option["label"]
                            for option in options["severities"]
                            if option["value"]
                            == applied_filters["severity"]
                        ),
                        applied_filters["severity"],
                    ),
                )
            )
        if applied_filters["operational_status"]:
            filter_labels.append(
                (
                    "Operational status",
                    next(
                        (
                            option["label"]
                            for option in options[
                                "operational_statuses"
                            ]
                            if option["value"]
                            == applied_filters[
                                "operational_status"
                            ]
                        ),
                        applied_filters["operational_status"],
                    ),
                )
            )

        equipment = result["equipment"]
        severity = result["analytics"]["severity"]
        equipment_total = equipment["total"]
        failure_total = severity["total"]
        recent_critical = result["details"]["recent_critical"][:1]
        equipment_attention = result["details"]["equipment_attention"][:1]
        overdue_parts = result["details"]["overdue_parts"][:1]
        recent_maintenance = result["details"]["recent_maintenance"][:1]
        detail_summary = {
            "recent_critical": {
                "total": result["inspections"]["critical"],
                "more": max(
                    0,
                    result["inspections"]["critical"]
                    - len(recent_critical),
                ),
            },
            "equipment_attention": {
                "total": (
                    equipment["maintenance"]
                    + equipment["out_of_service"]
                ),
                "more": max(
                    0,
                    equipment["maintenance"]
                    + equipment["out_of_service"]
                    - len(equipment_attention),
                ),
            },
            "overdue_parts": {
                "total": result["spare_parts"]["overdue"],
                "more": max(
                    0,
                    result["spare_parts"]["overdue"]
                    - len(overdue_parts),
                ),
            },
            "recent_maintenance": {
                "total": result["maintenance"]["open"],
                "more": max(
                    0,
                    result["maintenance"]["open"]
                    - len(recent_maintenance),
                ),
            },
        }

        def prepare_bars(rows, label_key, count_key, limit):
            selected = rows[-limit:] if label_key == "label" else rows[:limit]
            maximum = max(
                (row[count_key] for row in selected),
                default=0,
            )
            return [
                {
                    "label": row[label_key],
                    "count": row[count_key],
                    "equipment": ", ".join(
                        "%s (x%s)" % (item["name"], item["count"])
                        for item in row.get("equipment", [])
                    ),
                    "height": max(
                        2,
                        round(row[count_key] * 26 / maximum),
                    )
                    if maximum
                    else 2,
                    "width_style": "width: %s%%"
                    % (
                        min(
                            100,
                            round(row[count_key] * 100 / maximum),
                        )
                        if maximum
                        else 0
                    ),
                }
                for row in selected
            ]

        def prepare_donut(segments):
            circumference = 2 * 3.141592653589793 * 20
            offset = 0
            for segment in segments:
                length = circumference * segment["percent"] / 100
                segment["dasharray"] = (
                    f"{length:.2f} {circumference:.2f}"
                )
                segment["dashoffset"] = f"{-offset:.2f}"
                offset += length

        equipment_segments = [
            {
                "label": label,
                "count": equipment[key],
                "percent": round(equipment[key] * 100 / equipment_total)
                if equipment_total
                else 0,
                "color": color,
                "style": "width: %s%%; background: %s"
                % (
                    round(equipment[key] * 100 / equipment_total)
                    if equipment_total
                    else 0,
                    color,
                ),
            }
            for key, label, color in (
                ("active", "Active", "#79c9b1"),
                ("maintenance", "Maintenance", "#efbd72"),
                ("out_of_service", "Out of Service", "#df7e86"),
            )
        ]
        prepare_donut(equipment_segments)
        severity_segments = [
            {
                "label": label,
                "count": severity[key],
                "percent": round(severity[key] * 100 / failure_total)
                if failure_total
                else 0,
                "color": color,
                "style": "width: %s%%; background: %s"
                % (
                    round(severity[key] * 100 / failure_total)
                    if failure_total
                    else 0,
                    color,
                ),
            }
            for key, label, color in (
                ("low", "Low", "#79c9b1"),
                ("medium", "Medium", "#efbd72"),
                ("high", "High", "#e89a5b"),
                ("critical", "Critical", "#df7e86"),
            )
        ]
        prepare_donut(severity_segments)

        return {
            "doc_ids": docids,
            "doc_model": "res.company",
            "docs": self.env.company,
            "dashboard": result,
            "filter_labels": filter_labels,
            "availability_style": "width: %s%%"
            % min(max(equipment["availability_rate"], 0), 100),
            "pass_rate_style": "width: %s%%"
            % min(max(result["inspections"]["pass_rate"], 0), 100),
            "equipment_segments": equipment_segments,
            "severity_segments": severity_segments,
            "top_defects": prepare_bars(
                result["analytics"]["top_defects"],
                "name",
                "count",
                5,
            ),
            "category_bars": prepare_bars(
                result["analytics"]["category_failures"],
                "name",
                "count",
                5,
            ),
            "location_bars": prepare_bars(
                result["analytics"]["location_failures"],
                "name",
                "count",
                5,
            ),
            "detail_summary": detail_summary,
            "equipment_attention": equipment_attention,
            "recent_critical": recent_critical,
            "overdue_parts": overdue_parts,
            "recent_maintenance": recent_maintenance,
            "trend_bars": prepare_bars(
                result["analytics"]["inspection_trend"],
                "label",
                "count",
                12,
            ),
            "generated_at": fields.Datetime.context_timestamp(
                self, fields.Datetime.now()
            ).strftime("%Y-%m-%d %H:%M"),
        }
