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
        else:
            options.setdefault("date_from", str(today.replace(month=1, day=1)))
            options.setdefault("date_to", str(today))
        options.setdefault("target_move", "posted")
        options.setdefault("journal_ids", [])
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

        return {
            "title": title,
            "currency": company.currency_id.name,
            "company_name": company.name,
            "period_text": period_text,
            "comparison_text": comparison_text,
            "target_move": options.get("target_move"),
            "journals_text": ", ".join(journals) if journals else "All Journals",
            "analytics_text": ", ".join(analytics) if analytics else "All",
            "rows": rows,
            "options": options,
        }

    @api.model
    def _build_wizard_vals(self, options):
        vals = {
            "company_id": options.get("company_id") or self.env.company.id,
            "target_move": options.get("target_move") or "posted",
            "journal_ids": [(6, 0, options.get("journal_ids") or [])],
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
        wizard = self.env["ft.income.statement.wizard"].create(self._build_wizard_vals(options))
        return wizard.action_print()

    @api.model
    def export_xlsx(self, options):
        options = self._normalize_options(options)
        if options.get("report_type") == "balance_sheet":
            wizard = self.env["ft.balance.sheet.wizard"].create(self._build_wizard_vals(options))
            return wizard.check_report_xlsx()
        wizard = self.env["ft.income.statement.wizard"].create(self._build_wizard_vals(options))
        return wizard.check_report_xlsx()
