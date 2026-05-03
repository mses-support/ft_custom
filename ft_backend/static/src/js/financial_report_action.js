/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

class FtFinancialReportAction extends Component {
    static template = "ft_backend.FtFinancialReportAction";
    static components = { MultiRecordSelector };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const ctx = this.props.action.context || {};
        const now = new Date();
        const isoToday = now.toISOString().slice(0, 10);
        const startOfYear = `${now.getFullYear()}-01-01`;
        const inferredType = this._inferReportType(ctx);
        const isBalance = inferredType === "balance_sheet";
        const isCashFlow = inferredType === "cash_flow_custom";

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
                cash_flow_mode: "single",
                journal_ids: [],
                analytic_plan_ids: [],
                analytic_account_ids: [],
            },
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    _inferReportType(ctx) {
        if (ctx.report_type === "balance_sheet" || ctx.report_type === "income_statement" || ctx.report_type === "cash_flow_custom") {
            return ctx.report_type;
        }
        const actionName = (this.props.action?.name || "").toLowerCase();
        if (actionName.includes("balance")) {
            if (actionName.includes("cash flow")) {
            return "cash_flow_custom";
        }
        return "balance_sheet";
        }
        if (actionName.includes("income") || actionName.includes("profit") || actionName.includes("loss")) {
            return "income_statement";
        }
        if (actionName.includes("cash flow")) {
            return "cash_flow_custom";
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


FtFinancialReportAction.prototype.onJournalIdsChange = function (resIds) {
    this.state.options.journal_ids = resIds || [];
};

FtFinancialReportAction.prototype.onCashFlowModeChange = function (ev) {
    this.state.options.cash_flow_mode = ev.target.value || "single";
};

FtFinancialReportAction.prototype.onAnalyticPlanIdsChange = function (resIds) {
    this.state.options.analytic_plan_ids = resIds || [];
};

FtFinancialReportAction.prototype.onAnalyticAccountIdsChange = function (resIds) {
    this.state.options.analytic_account_ids = resIds || [];
};
