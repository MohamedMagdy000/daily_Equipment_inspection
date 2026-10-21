{
    "name": "Daily Equipment Report",

    "version": "20.0.1.0.0",

    "summary": (
        "Equipment inspections, maintenance integration, "
        "spare-part reminders and dashboard"
    ),

    "description": """
Daily Equipment Report
======================

Extends Odoo Maintenance to provide:

- Inspection checklist questions by equipment category
- Daily equipment inspection reports and approval workflow
- Issue photos and descriptions for failed checks
- Automatic corrective maintenance requests from failed inspections
- Spare-part maintenance cycles and reminders
- Equipment operational status and inspection history
- Equipment management dashboard with filters, KPIs and analytics
    """,

    "category": "Operations/Maintenance",

    "author": "Custom Development",

    "license": "LGPL-3",

    "depends": [
        "base",
        "mail",
        "maintenance",
        "hr",
        "web",
    ],

    "data": [
    "security/security.xml",
    "security/maintenance_group_bridge.xml",
    "data/ir_cron_data.xml",
    "data/equipment_daily_report_sequence.xml",
    "report/equipment_daily_report_templates.xml",
    "report/equipment_dashboard_report.xml",
    "views/equipment_checklist_question_views.xml",
    "views/inherited_equipment_category_views.xml",
    "views/inherited_equipment_views.xml",
    "views/equipment_daily_report_views.xml",
    "views/inspection_maintenance_bridge_views.xml",
    "views/equipment_spare_part_views.xml",
    "views/res_users_views.xml",
    "views/equipment_dashboard_views.xml",
    "views/menu.xml",
],

    "assets": {

        "web.assets_backend": [

            "daily_equipment_report/"
            "static/src/js/"
            "equipment_dashboard.js",

            "daily_equipment_report/"
            "static/src/xml/"
            "equipment_dashboard.xml",

            "daily_equipment_report/"
            "static/src/scss/"
            "equipment_dashboard.scss",
        ],
    },

    "installable": True,

    "application": True,
}