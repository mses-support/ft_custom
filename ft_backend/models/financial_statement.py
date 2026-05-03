from odoo import api, fields, models
from odoo.addons.base_accounting_kit.wizard.xlsx_mixin import ReportXlsxMixin
from odoo.exceptions import ValidationError


class FtFinancialReportConfig(models.Model):
    _name = "ft.financial.report.config"
    _description = "Financial Report Configuration"
    _order = "statement_type, sequence, id"

    name = fields.Char(required=True)
    statement_type = fields.Selection(
        [
            ("balance_sheet", "Balance Sheet"),
            ("income_statement", "Income Statement"),
            ("cash_flow_custom", "Cash Flow Statement"),
        ],
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("ft.financial.report.config.line", "config_id", string="Lines")


class FtFinancialReportConfigLine(models.Model):
    _name = "ft.financial.report.config.line"
    _description = "Financial Report Configuration Line"
    _order = "sequence, id"

    config_id = fields.Many2one("ft.financial.report.config", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    code = fields.Char(required=True)
    name = fields.Char(required=True)
    parent_code = fields.Char()
    level = fields.Integer(default=1)
    is_total = fields.Boolean(default=False)
    sign = fields.Selection(
        [("normal", "Normal"), ("invert", "Invert Sign")],
        default="normal",
        required=True,
    )
    account_ids = fields.Many2many("account.account", string="Accounts")

    _sql_constraints = [
        ("code_uniq_per_config", "unique(config_id, code)", "Line code must be unique per configuration."),
    ]

    @api.constrains("parent_code", "code")
    def _check_parent(self):
        for rec in self:
            if rec.parent_code and rec.parent_code == rec.code:
                raise ValidationError("Parent code cannot be same as line code.")


class FtBalanceSheetWizard(models.TransientModel, ReportXlsxMixin):
    _name = "ft.balance.sheet.wizard"
    _description = "Balance Sheet Wizard"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, readonly=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")], default="posted", required=True
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)
    journal_ids = fields.Many2many("account.journal", string="Journals")
    analytic_account_ids = fields.Many2many("account.analytic.account", string="Analytic Accounts")
    comparison_date_to = fields.Date(string="Comparison As of")

    def action_print(self):
        self.ensure_one()
        data = {
            "form": self.read(
                [
                    "company_id",
                    "date_to",
                    "target_move",
                    "currency_id",
                    "journal_ids",
                    "analytic_account_ids",
                    "comparison_date_to",
                ]
            )[0]
        }
        return self.env.ref("ft_backend.action_report_balance_sheet_custom").report_action(self, data=data)

    def action_view(self):
        self.ensure_one()
        data = {
            "form": self.read(
                [
                    "company_id",
                    "date_to",
                    "target_move",
                    "currency_id",
                    "journal_ids",
                    "analytic_account_ids",
                    "comparison_date_to",
                ]
            )[0]
        }
        action = self.env.ref("ft_backend.action_report_balance_sheet_custom_html", raise_if_not_found=False)
        if not action:
            action = self.env.ref("ft_backend.action_report_balance_sheet_custom")
        return action.report_action(self, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        form = self.read(
            [
                "company_id",
                "date_to",
                "target_move",
                "currency_id",
                "journal_ids",
                "analytic_account_ids",
                "comparison_date_to",
            ]
        )[0]
        report_model = self.env["report.ft_backend.report_balance_sheet_custom"]
        company_id = report_model._as_id(form.get("company_id")) or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        config = report_model._config("balance_sheet", company_id)
        rows = report_model._build_lines(
            config,
            company_id,
            form.get("target_move"),
            date_to=form.get("date_to"),
            journal_ids=form.get("journal_ids") or [],
            analytic_account_ids=form.get("analytic_account_ids") or [],
            comparison_date_to=form.get("comparison_date_to"),
        )
        options = {
            "company_name": company.name or "",
            "company_logo": company.logo,
            "report_name": "Balance Sheet",
            "period_text": f"As at {report_model._fmt_date(form.get('date_to'))}",
            "currency": company.currency_id.name,
            "rows": rows,
        }
        return self._xlsx_action("ft.balance.sheet.wizard", "Balance Sheet", options)

    def get_xlsx_report(self, data, response):
        rows = []
        for row in data.get("rows", []):
            name = "%s%s" % ("  " * int(row.get("level", 0)), row.get("name", ""))
            rows.append(
                {
                    "type": "section" if row.get("is_total") or int(row.get("level", 0)) <= 1 else "data",
                    "values": [name, float(row.get("amount", 0.0)), float(row.get("comparison_amount", 0.0))],
                }
            )
        table = {
            "sheet_name": "Balance Sheet",
            "title": f"{data.get('company_name', '')}: {data.get('report_name', 'Balance Sheet')}",
            "company_logo": data.get("company_logo"),
            "meta": [("Period:", data.get("period_text")), ("Currency:", data.get("currency"))],
            "headers": ["Particulars", "Balance", "Comparison"],
            "column_widths": [(0, 0, 54), (1, 2, 20)],
            "rows": rows,
        }
        self._render_xlsx_table(table, response)


class FtIncomeStatementWizard(models.TransientModel, ReportXlsxMixin):
    _name = "ft.income.statement.wizard"
    _description = "Income Statement Wizard"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, readonly=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")], default="posted", required=True
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)
    journal_ids = fields.Many2many("account.journal", string="Journals")
    analytic_plan_ids = fields.Many2many("account.analytic.plan", string="Analytic Plans")
    analytic_account_ids = fields.Many2many("account.analytic.account", string="Analytic Accounts")
    comparison_date_from = fields.Date(string="Comparison From")
    comparison_date_to = fields.Date(string="Comparison To")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("Date From must be before or equal to Date To.")

    def action_print(self):
        self.ensure_one()
        data = {
            "form": self.read(
                [
                    "company_id",
                    "date_from",
                    "date_to",
                    "target_move",
                    "currency_id",
                    "journal_ids",
                    "analytic_plan_ids",
                    "analytic_account_ids",
                    "comparison_date_from",
                    "comparison_date_to",
                ]
            )[0]
        }
        return self.env.ref("ft_backend.action_report_income_statement_custom").report_action(self, data=data)

    def action_view(self):
        self.ensure_one()
        data = {
            "form": self.read(
                [
                    "company_id",
                    "date_from",
                    "date_to",
                    "target_move",
                    "currency_id",
                    "journal_ids",
                    "analytic_plan_ids",
                    "analytic_account_ids",
                    "comparison_date_from",
                    "comparison_date_to",
                ]
            )[0]
        }
        action = self.env.ref("ft_backend.action_report_income_statement_custom_html", raise_if_not_found=False)
        if not action:
            action = self.env.ref("ft_backend.action_report_income_statement_custom")
        return action.report_action(self, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        form = self.read(
            [
                "company_id",
                "date_from",
                "date_to",
                "target_move",
                "currency_id",
                "journal_ids",
                "analytic_plan_ids",
                "analytic_account_ids",
                "comparison_date_from",
                "comparison_date_to",
            ]
        )[0]
        report_model = self.env["report.ft_backend.report_income_statement_custom"]
        company_id = report_model._as_id(form.get("company_id")) or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        config = report_model._config("income_statement", company_id)
        rows = report_model._build_lines(
            config,
            company_id,
            form.get("target_move"),
            date_from=form.get("date_from"),
            date_to=form.get("date_to"),
            journal_ids=form.get("journal_ids") or [],
            analytic_plan_ids=form.get("analytic_plan_ids") or [],
            analytic_account_ids=form.get("analytic_account_ids") or [],
            comparison_date_from=form.get("comparison_date_from"),
            comparison_date_to=form.get("comparison_date_to"),
        )
        options = {
            "company_name": company.name or "",
            "company_logo": company.logo,
            "report_name": "Income Statement",
            "period_text": (
                f"From {report_model._fmt_date(form.get('date_from'))} "
                f"to {report_model._fmt_date(form.get('date_to'))}"
            ),
            "currency": company.currency_id.name,
            "rows": rows,
        }
        return self._xlsx_action("ft.income.statement.wizard", "Income Statement", options)

    def get_xlsx_report(self, data, response):
        rows = []
        for row in data.get("rows", []):
            name = "%s%s" % ("  " * int(row.get("level", 0)), row.get("name", ""))
            rows.append(
                {
                    "type": "section" if row.get("is_total") or int(row.get("level", 0)) <= 1 else "data",
                    "values": [name, float(row.get("amount", 0.0)), float(row.get("comparison_amount", 0.0))],
                }
            )
        table = {
            "sheet_name": "Income Statement",
            "title": f"{data.get('company_name', '')}: {data.get('report_name', 'Income Statement')}",
            "company_logo": data.get("company_logo"),
            "meta": [("Period:", data.get("period_text")), ("Currency:", data.get("currency"))],
            "headers": ["Particulars", "Amount", "Comparison"],
            "column_widths": [(0, 0, 54), (1, 2, 20)],
            "rows": rows,
        }
        self._render_xlsx_table(table, response)
