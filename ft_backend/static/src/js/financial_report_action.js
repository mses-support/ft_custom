/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class FtFinancialReportAction extends Component {
    static template = "ft_backend.FtFinancialReportAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const ctx = this.props.action.context || {};
        const now = new Date();
        const isoToday = now.toISOString().slice(0, 10);
        const startOfYear = `${now.getFullYear()}-01-01`;
        const inferredType = this._inferReportType(ctx);
        const isBalance = inferredType === "balance_sheet";

        this.state = useState({
            loading: true,
            report: null,
            options: {
                report_type: inferredType,
                company_id: ctx.company_id || false,
                date_from: isBalance ? null : startOfYear,
                date_to: isoToday,
                comparison_date_from: null,
                comparison_date_to: null,
                target_move: "posted",
                journal_ids: [],
                analytic_account_ids: [],
            },
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    _inferReportType(ctx) {
        if (ctx.report_type === "balance_sheet" || ctx.report_type === "income_statement") {
            return ctx.report_type;
        }
        const actionName = (this.props.action?.name || "").toLowerCase();
        if (actionName.includes("balance")) {
            return "balance_sheet";
        }
        if (actionName.includes("income") || actionName.includes("profit") || actionName.includes("loss")) {
            return "income_statement";
        }
        return "balance_sheet";
    }

    async loadReport() {
        this.state.loading = true;
        this.state.report = await this.orm.call(
            "ft.dynamic.financial.report.service",
            "get_report_data",
            [this.state.options]
        );
        this.state.loading = false;
    }

    async onApplyFilter() {
        await this.loadReport();
    }

    onInputDate(field, ev) {
        this.state.options[field] = ev.target.value || null;
    }

    onTargetMove(ev) {
        this.state.options.target_move = ev.target.value;
    }

    async onExportPdf() {
        const action = await this.orm.call(
            "ft.dynamic.financial.report.service",
            "export_pdf",
            [this.state.options]
        );
        await this.action.doAction(action);
    }

    async onExportXlsx() {
        const action = await this.orm.call(
            "ft.dynamic.financial.report.service",
            "export_xlsx",
            [this.state.options]
        );
        await this.action.doAction(action);
    }
}

registry.category("actions").add("ft_financial_report", FtFinancialReportAction);
