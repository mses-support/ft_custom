from odoo import api, fields, models


class FtDynamicFinancialReportService(models.AbstractModel):
    _name = "ft.dynamic.financial.report.service"
    _description = "Dynamic Financial Report Service"

    @api.model
    def _normalize_options(self, options):
        options = dict(options or {})
        report_type = options.get("report_type") or "balance_sheet"
        today = fields.Date.context_today(self)
        if report_type == "balance_sheet":
            options.setdefault("date_to", str(today))
        elif report_type == "cash_flow_custom":
            options.setdefault("date_from", str(today.replace(month=1, day=1)))
            options.setdefault("date_to", str(today))
        else:
            options.setdefault("date_from", str(today.replace(month=1, day=1)))
            options.setdefault("date_to", str(today))
        options.setdefault("target_move", "posted")
        options.setdefault("cash_flow_mode", "single")
        options.setdefault("journal_ids", [])
        options.setdefault("analytic_plan_ids", [])
        options.setdefault("analytic_account_ids", [])
        return options

    @api.model
    def get_report_data(self, options):
        options = self._normalize_options(options)
        report_type = options["report_type"]

        if report_type == "balance_sheet":
            report_model = self.env["report.ft_backend.report_balance_sheet_custom"]
            company_id = report_model._as_id(options.get("company_id")) or self.env.company.id
            company = self.env["res.company"].browse(company_id)
            config = report_model._config("balance_sheet", company_id)
            rows = report_model._build_lines(
                config,
                company_id,
                options.get("target_move"),
                date_to=options.get("date_to"),
                journal_ids=options.get("journal_ids") or [],
                analytic_account_ids=options.get("analytic_account_ids") or [],
                comparison_date_to=options.get("comparison_date_to"),
            )
            title = "Balance Sheet"
            period_text = f"As of {report_model._fmt_date(options.get('date_to'))}"
            comparison_text = report_model._fmt_date(options.get("comparison_date_to")) if options.get("comparison_date_to") else ""
        elif report_type == "cash_flow_custom":
            report_model = self.env["report.ft_backend.report_custom_cash_flow_statement"]
            prepared = report_model._prepare_statement({
                'company_id': options.get('company_id') or self.env.company.id,
                'date_from': options.get('date_from'),
                'date_to': options.get('date_to'),
                'target_move': options.get('target_move'),
                'journal_ids': options.get('journal_ids') or [],
                'analytic_plan_ids': options.get('analytic_plan_ids') or [],
                'analytic_account_ids': options.get('analytic_account_ids') or [],
            })
            company = prepared['company']
            m = prepared['mapped']
            op = m.get('operations', {})
            inv = m.get('investing', {})
            fin = m.get('financing', {})
            rows = [
                {'code': 'OP', 'name': 'Operations', 'level': 0, 'is_total': False, 'amount': 0.0, 'comparison_amount': 0.0},
                {'code': 'OP1', 'name': 'Cash receipts from Customers', 'level': 2, 'is_total': False, 'amount': op.get('cash_receipts_customers', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP2', 'name': 'Cash receipts from Other Operations', 'level': 2, 'is_total': False, 'amount': op.get('cash_receipts_other', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP3', 'name': 'Cash paid for Inventory purchases', 'level': 2, 'is_total': False, 'amount': op.get('cash_paid_inventory', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP4', 'name': 'Cash paid for General operating and administrative expenses', 'level': 2, 'is_total': False, 'amount': op.get('cash_paid_general_admin', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP5', 'name': 'Cash paid for Wage expenses', 'level': 2, 'is_total': False, 'amount': op.get('cash_paid_wages', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP6', 'name': 'Cash paid for Interest', 'level': 2, 'is_total': False, 'amount': op.get('cash_paid_interest', 0.0), 'comparison_amount': 0.0},
                {'code': 'OP7', 'name': 'Cash paid for Income taxes', 'level': 2, 'is_total': False, 'amount': op.get('cash_paid_income_taxes', 0.0), 'comparison_amount': 0.0},
                {'code': 'OPT', 'name': 'Net Cash Flow from Operations', 'level': 1, 'is_total': True, 'amount': op.get('net', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV', 'name': 'Investing Activities', 'level': 0, 'is_total': False, 'amount': 0.0, 'comparison_amount': 0.0},
                {'code': 'INV1', 'name': 'Sale of property and equipment', 'level': 2, 'is_total': False, 'amount': inv.get('cash_receipts_sale_ppe', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV2', 'name': 'Collection of principal on loans', 'level': 2, 'is_total': False, 'amount': inv.get('cash_receipts_collection_loans', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV3', 'name': 'Sale of investment securities', 'level': 2, 'is_total': False, 'amount': inv.get('cash_receipts_sale_investments', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV4', 'name': 'Purchase of property and equipment', 'level': 2, 'is_total': False, 'amount': inv.get('cash_paid_purchase_ppe', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV5', 'name': 'Making loans to other entities', 'level': 2, 'is_total': False, 'amount': inv.get('cash_paid_loans_to_others', 0.0), 'comparison_amount': 0.0},
                {'code': 'INV6', 'name': 'Purchase of investment securities', 'level': 2, 'is_total': False, 'amount': inv.get('cash_paid_purchase_investments', 0.0), 'comparison_amount': 0.0},
                {'code': 'INVT', 'name': 'Net Cash Flow from Investing Activities', 'level': 1, 'is_total': True, 'amount': inv.get('net', 0.0), 'comparison_amount': 0.0},
                {'code': 'FIN', 'name': 'Financing Activities', 'level': 0, 'is_total': False, 'amount': 0.0, 'comparison_amount': 0.0},
                {'code': 'FIN1', 'name': 'Issuance of stock', 'level': 2, 'is_total': False, 'amount': fin.get('cash_receipts_issuance_stock', 0.0), 'comparison_amount': 0.0},
                {'code': 'FIN2', 'name': 'Borrowing', 'level': 2, 'is_total': False, 'amount': fin.get('cash_receipts_borrowing', 0.0), 'comparison_amount': 0.0},
                {'code': 'FIN3', 'name': 'Repurchase of stock (treasury stock)', 'level': 2, 'is_total': False, 'amount': fin.get('cash_paid_treasury_stock', 0.0), 'comparison_amount': 0.0},
                {'code': 'FIN4', 'name': 'Repayment of loans', 'level': 2, 'is_total': False, 'amount': fin.get('cash_paid_repayment_loans', 0.0), 'comparison_amount': 0.0},
                {'code': 'FIN5', 'name': 'Dividends', 'level': 2, 'is_total': False, 'amount': fin.get('cash_paid_dividends', 0.0), 'comparison_amount': 0.0},
                {'code': 'FINT', 'name': 'Net Cash Flow from Financing Activities', 'level': 1, 'is_total': True, 'amount': fin.get('net', 0.0), 'comparison_amount': 0.0},
                {'code': 'NET', 'name': 'Net Increase in Cash', 'level': 1, 'is_total': True, 'amount': m.get('net_increase', 0.0), 'comparison_amount': 0.0},
                {'code': 'OPEN', 'name': 'Cash at Beginning of Year', 'level': 1, 'is_total': False, 'amount': prepared.get('opening_cash', 0.0), 'comparison_amount': 0.0},
                {'code': 'CLOSE', 'name': 'Cash at End of Year', 'level': 1, 'is_total': True, 'amount': prepared.get('closing_cash', 0.0), 'comparison_amount': 0.0},
            ]
            title = "Cash Flow Statement"
            period_text = (
                f"From {report_model._to_date_string(options.get('date_from'))} "
                f"to {report_model._to_date_string(options.get('date_to'))}"
            )
            comparison_text = ""
        else:
            report_model = self.env["report.ft_backend.report_income_statement_custom"]
            company_id = report_model._as_id(options.get("company_id")) or self.env.company.id
            company = self.env["res.company"].browse(company_id)
            config = report_model._config("income_statement", company_id)
            rows = report_model._build_lines(
                config,
                company_id,
                options.get("target_move"),
                date_from=options.get("date_from"),
                date_to=options.get("date_to"),
                journal_ids=options.get("journal_ids") or [],
                analytic_account_ids=options.get("analytic_account_ids") or [],
                analytic_plan_ids=options.get("analytic_plan_ids") or [],
                comparison_date_from=options.get("comparison_date_from"),
                comparison_date_to=options.get("comparison_date_to"),
            )
            title = "Income Statement"
            period_text = (
                f"From {report_model._fmt_date(options.get('date_from'))} "
                f"to {report_model._fmt_date(options.get('date_to'))}"
            )
            if options.get("comparison_date_from") and options.get("comparison_date_to"):
                comparison_text = (
                    f"{report_model._fmt_date(options.get('comparison_date_from'))} - "
                    f"{report_model._fmt_date(options.get('comparison_date_to'))}"
                )
            else:
                comparison_text = ""

        journals = self.env["account.journal"].browse(options.get("journal_ids") or []).mapped("name")
        analytics = self.env["account.analytic.account"].browse(options.get("analytic_account_ids") or []).mapped("name")
        analytic_plans = self.env["account.analytic.plan"].browse(options.get("analytic_plan_ids") or []).mapped("name")

        return {
            "title": title,
            "currency": company.currency_id.name,
            "company_name": company.name,
            "period_text": period_text,
            "comparison_text": comparison_text,
            "target_move": options.get("target_move"),
            "journals_text": ", ".join(journals) if journals else "All Journals",
            "analytics_text": ", ".join(analytics) if analytics else "All",
            "analytic_plans_text": ", ".join(analytic_plans) if analytic_plans else "All",
            "rows": rows,
            "options": options,
        }

    @api.model
    def _build_wizard_vals(self, options):
        vals = {
            "company_id": options.get("company_id") or self.env.company.id,
            "target_move": options.get("target_move") or "posted",
            "journal_ids": [(6, 0, options.get("journal_ids") or [])],
            "analytic_plan_ids": [(6, 0, options.get("analytic_plan_ids") or [])],
            "analytic_account_ids": [(6, 0, options.get("analytic_account_ids") or [])],
        }
        if options.get("report_type") == "balance_sheet":
            vals.update(
                {
                    "date_to": options.get("date_to"),
                    "comparison_date_to": options.get("comparison_date_to") or False,
                }
            )
        else:
            vals.update(
                {
                    "date_from": options.get("date_from"),
                    "date_to": options.get("date_to"),
                    "comparison_date_from": options.get("comparison_date_from") or False,
                    "comparison_date_to": options.get("comparison_date_to") or False,
                }
            )
        return vals

    @api.model
    def export_pdf(self, options):
        options = self._normalize_options(options)
        if options.get("report_type") == "balance_sheet":
            wizard = self.env["ft.balance.sheet.wizard"].create(self._build_wizard_vals(options))
            return wizard.action_print()
        if options.get("report_type") == "cash_flow_custom":
            wizard = self.env["ft.custom.cash.flow.statement"].create({
                'company_id': options.get('company_id') or self.env.company.id,
                'date_from': options.get('date_from'),
                'date_to': options.get('date_to'),
                'target_move': options.get('target_move') or 'posted',
                'cash_flow_mode': options.get('cash_flow_mode') or 'single',
                'journal_ids': [(6, 0, options.get('journal_ids') or [])],
                'analytic_plan_ids': [(6, 0, options.get('analytic_plan_ids') or [])],
                'analytic_account_ids': [(6, 0, options.get('analytic_account_ids') or [])],
            })
            return wizard.action_print()
        wizard = self.env["ft.income.statement.wizard"].create(self._build_wizard_vals(options))
        return wizard.action_print()

    @api.model
    def export_xlsx(self, options):
        options = self._normalize_options(options)
        if options.get("report_type") == "balance_sheet":
            wizard = self.env["ft.balance.sheet.wizard"].create(self._build_wizard_vals(options))
            return wizard.check_report_xlsx()
        if options.get("report_type") == "cash_flow_custom":
            wizard = self.env["ft.custom.cash.flow.statement"].create({
                'company_id': options.get('company_id') or self.env.company.id,
                'date_from': options.get('date_from'),
                'date_to': options.get('date_to'),
                'target_move': options.get('target_move') or 'posted',
                'cash_flow_mode': options.get('cash_flow_mode') or 'single',
                'journal_ids': [(6, 0, options.get('journal_ids') or [])],
                'analytic_plan_ids': [(6, 0, options.get('analytic_plan_ids') or [])],
                'analytic_account_ids': [(6, 0, options.get('analytic_account_ids') or [])],
            })
            return wizard.check_report_xlsx()
        wizard = self.env["ft.income.statement.wizard"].create(self._build_wizard_vals(options))
        return wizard.check_report_xlsx()
