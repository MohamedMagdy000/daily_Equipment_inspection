/** @odoo-module **/

import {
    Component,
    onWillStart,
    proxy,
} from "@odoo/owl";

import {
    registry,
} from "@web/core/registry";

import {
    useService,
} from "@web/core/utils/hooks";


export class EquipmentInspectionDashboard
    extends Component {

    setup() {

        this.orm =
            useService("orm");

        this.action =
            useService("action");

        this.notification =
            useService(
                "notification"
            );

        const today =
            new Date();

        const fromDate =
            new Date(today);

        fromDate.setDate(
            today.getDate() - 29
        );

        this.state = proxy({

            loading: true,

            printing: false,

            data: null,

            hover: {
                equipment: "",
                severity: "",
            },

            filters: {

                date_from:
                    this.formatInputDate(
                        fromDate
                    ),

                date_to:
                    this.formatInputDate(
                        today
                    ),

                category_id:
                    false,

                equipment_id:
                    false,

                location:
                    "",

                severity:
                    "",

                operational_status:
                    "",
            },
        });

        onWillStart(
            async () => {

                await this.loadDashboard();

            }
        );
    }

    formatInputDate(date) {

        const year =
            date.getFullYear();

        const month =
            String(
                date.getMonth() + 1
            ).padStart(
                2,
                "0"
            );

        const day =
            String(
                date.getDate()
            ).padStart(
                2,
                "0"
            );

        return (
            `${year}-${month}-${day}`
        );
    }

    async loadDashboard() {

        this.state.loading =
            true;

        try {

            const data =
                await this.orm.call(

                    "equipment.inspection.dashboard",

                    "get_dashboard_data",

                    [
                        this.state.filters,
                    ]
                );

            this.state.data =
                data;

        } catch (error) {

            this.notification.add(
                "Unable to load the equipment dashboard.",
                {
                    type: "danger",
                }
            );

            throw error;

        } finally {

            this.state.loading =
                false;
        }
    }

    async applyFilters() {

        await this.loadDashboard();

    }

    async resetFilters() {

        const today =
            new Date();

        const fromDate =
            new Date(today);

        fromDate.setDate(
            today.getDate() - 29
        );

        Object.assign(
            this.state.filters,
            {
                date_from:
                    this.formatInputDate(
                        fromDate
                    ),

                date_to:
                    this.formatInputDate(
                        today
                    ),

                category_id:
                    false,

                equipment_id:
                    false,

                location:
                    "",

                severity:
                    "",

                operational_status:
                    "",
            }
        );

        await this.loadDashboard();
    }

    async printDashboard() {
        this.state.printing = true;
        try {
            const action = await this.orm.call(
                "equipment.inspection.dashboard",
                "action_print_dashboard",
                [this.state.filters]
            );
            await this.action.doAction(action);
        } catch (error) {
            this.notification.add(
                "Unable to print the equipment dashboard.",
                { type: "danger" }
            );
            throw error;
        } finally {
            this.state.printing = false;
        }
    }

    onCategoryChange(ev) {

        const value =
            Number(
                ev.target.value
                || 0
            );

        this.state.filters
            .category_id =
            value || false;

        if (
            this.state.filters
                .equipment_id
        ) {

            const selected =
                this
                .filteredEquipmentOptions
                .find(
                    (item) =>
                        item.id
                        ===
                        this.state.filters
                            .equipment_id
                );

            if (!selected) {

                this.state.filters
                    .equipment_id =
                    false;
            }
        }
    }

    onEquipmentChange(ev) {

        const value =
            Number(
                ev.target.value
                || 0
            );

        this.state.filters
            .equipment_id =
            value || false;
    }

    onLocationChange(ev) {

        this.state.filters
            .location =
            ev.target.value || "";
    }

    onSeverityChange(ev) {

        this.state.filters
            .severity =
            ev.target.value || "";
    }

    onOperationalStatusChange(
        ev
    ) {

        this.state.filters
            .operational_status =
            ev.target.value || "";
    }

    onDateFromChange(ev) {

        this.state.filters
            .date_from =
            ev.target.value;
    }

    onDateToChange(ev) {

        this.state.filters
            .date_to =
            ev.target.value;
    }

    get filteredEquipmentOptions() {

        const options =
            this.state.data
                ?.filter_options
                ?.equipments
            || [];

        if (
            !this.state.filters
                .category_id
        ) {

            return options;
        }

        return options.filter(
            (item) =>
                item.category_id
                ===
                this.state.filters
                    .category_id
        );
    }

    percent(value) {

        return (
            `${Math.max(
                0,
                Math.min(
                    100,
                    Number(value || 0)
                )
            )}%`
        );
    }

    barWidth(
        value,
        rows,
    ) {

        const max =
            Math.max(
                ...(
                    rows || []
                ).map(
                    (row) =>
                        Number(
                            row.count
                            || 0
                        )
                ),
                1
            );

        return (
            `${Math.max(
                4,
                (
                    Number(
                        value || 0
                    )
                    / max
                )
                * 100
            )}%`
        );
    }

    trendHeight(value) {

        const rows =
            this.state.data
                ?.analytics
                ?.inspection_trend
            || [];

        const max =
            Math.max(
                ...rows.map(
                    (row) =>
                        Number(
                            row.count
                            || 0
                        )
                ),
                1
            );

        return (
            `${Math.max(
                4,
                (
                    Number(
                        value || 0
                    )
                    / max
                )
                * 100
            )}%`
        );
    }

    get equipmentDonutStyle() {

        const equipment =
            this.state.data
                ?.equipment
            || {};

        const total =
            Math.max(
                Number(
                    equipment.total
                    || 0
                ),
                1
            );

        const active =
            (
                Number(
                    equipment.active
                    || 0
                )
                / total
            )
            * 100;

        const maintenance =
            (
                Number(
                    equipment.maintenance
                    || 0
                )
                / total
            )
            * 100;

        const stop =
            active
            + maintenance;

        return (
            "background: "
            + "conic-gradient("
            + "#70cfa5 0 "
            + `${active}%, `
            + "#f0bd72 "
            + `${active}% `
            + `${stop}%, `
            + "#df7e86 "
            + `${stop}% 100%`
            + ");"
        );
    }

    get severityDonutStyle() {

        const severity =
            this.state.data
                ?.analytics
                ?.severity
            || {};

        const total =
            Math.max(
                Number(
                    severity.total
                    || 0
                ),
                1
            );

        const low =
            (
                Number(
                    severity.low
                    || 0
                )
                / total
            )
            * 100;

        const medium =
            (
                Number(
                    severity.medium
                    || 0
                )
                / total
            )
            * 100;

        const high =
            (
                Number(
                    severity.high
                    || 0
                )
                / total
            )
            * 100;

        const mediumStop =
            low
            + medium;

        const highStop =
            mediumStop
            + high;

        return (
            "background: "
            + "conic-gradient("
            + "#79c9b1 0 "
            + `${low}%, `
            + "#efbd72 "
            + `${low}% `
            + `${mediumStop}%, `
            + "#e89a5b "
            + `${mediumStop}% `
            + `${highStop}%, `
            + "#df7e86 "
            + `${highStop}% 100%`
            + ");"
        );
    }

    get equipmentHoverValue() {
        const key = this.state.hover.equipment;
        if (!key) {
            return this.state.data?.equipment?.total || 0;
        }
        return this.state.data?.equipment?.[key] || 0;
    }

    get equipmentHoverLabel() {
        const labels = {
            active: "Active",
            maintenance: "Maintenance",
            out_of_service: "Out of Service",
        };
        return labels[this.state.hover.equipment] || "Total";
    }

    get severityHoverValue() {
        const key = this.state.hover.severity;
        if (!key) {
            return this.state.data?.analytics?.severity?.total || 0;
        }
        return this.state.data?.analytics?.severity?.[key] || 0;
    }

    get severityHoverLabel() {
        const labels = {
            low: "Low",
            medium: "Medium",
            high: "High",
            critical: "Critical",
        };
        return labels[this.state.hover.severity] || "Failures";
    }

    equipmentPercent(key) {
        const equipment = this.state.data?.equipment || {};
        const total = Number(equipment.total || 0);
        if (!total) {
            return 0;
        }
        return Math.round((Number(equipment[key] || 0) / total) * 100);
    }

    severityPercent(key) {
        const severity = this.state.data?.analytics?.severity || {};
        const total = Number(severity.total || 0);
        if (!total) {
            return 0;
        }
        return Math.round((Number(severity[key] || 0) / total) * 100);
    }

    setEquipmentHover(ev) {
        this.state.hover.equipment = ev.currentTarget.dataset.status || "";
    }

    clearEquipmentHover() {
        this.state.hover.equipment = "";
    }

    setSeverityHover(ev) {
        this.state.hover.severity = ev.currentTarget.dataset.severity || "";
    }

    clearSeverityHover() {
        this.state.hover.severity = "";
    }

    async openEquipmentList(ev) {
        const status = ev?.currentTarget?.dataset?.status || false;

        const action = await this.orm.call(
            "equipment.inspection.dashboard",
            "action_open_equipment_list",
            [this.state.filters, status]
        );

        if (action) {
            await this.action.doAction(action);
        }
    }

    async openSeverityInspections(ev) {
        const severity = ev?.currentTarget?.dataset?.severity || false;

        const action = await this.orm.call(
            "equipment.inspection.dashboard",
            "action_open_severity_inspections",
            [this.state.filters, severity]
        );

        if (action) {
            await this.action.doAction(action);
        }
    }

    async openInspection(ev) {

        const id =
            Number(
                ev.currentTarget
                    .dataset.id
            );

        if (id) {

            const action =
                await this.orm.call(

                    "equipment.inspection.dashboard",

                    "action_open_inspection",

                    [id]
                );

            if (action) {

                await this.action
                    .doAction(
                        action
                    );
            }
        }
    }

    async openEquipment(ev) {

        const id =
            Number(
                ev.currentTarget
                    .dataset.id
            );

        if (id) {

            const action =
                await this.orm.call(

                    "equipment.inspection.dashboard",

                    "action_open_equipment",

                    [id]
                );

            if (action) {

                await this.action
                    .doAction(
                        action
                    );
            }
        }
    }

    async openMaintenance(ev) {

        const id =
            Number(
                ev.currentTarget
                    .dataset.id
            );

        if (id) {

            const action =
                await this.orm.call(

                    "equipment.inspection.dashboard",

                    "action_open_maintenance_request",

                    [id]
                );

            if (action) {

                await this.action
                    .doAction(
                        action
                    );
            }
        }
    }
}

EquipmentInspectionDashboard.template =
    "daily_equipment_report."
    + "EquipmentInspectionDashboard";


registry
    .category("actions")
    .add(
        "daily_equipment_report."
        + "equipment_dashboard",

        EquipmentInspectionDashboard
    );
