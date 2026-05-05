from odoo import api, fields, models
from odoo.exceptions import UserError


class FinancialStatementReportMixin(models.AbstractModel):
    _name = "report.ft_backend.financial_statement_mixin"
    _description = "Financial Statement Mixin"

    @api.model
    def _as_id(self, value):
        if isinstance(value, (list, tuple)):
            return value[0]
        return value

    @api.model
    def _fmt_date(self, value):
        if not value:
            return ""
        return fields.Date.to_date(value).strftime("%d %b %Y")

    @api.model
    def _config(self, statement_type, company_id):
        return self.env["ft.financial.report.config"].search(
            [
                ("statement_type", "=", statement_type),
                ("company_id", "=", company_id),
                ("active", "=", True),
            ],
            limit=1,
            order="sequence, id",
        )

    @api.model
    def _sum_accounts(
        self,
        account_ids,
        company_id,
        target_move,
        date_from=None,
        date_to=None,
        journal_ids=None,
        analytic_plan_ids=None,
        analytic_account_ids=None,
    ):
        if not account_ids:
            return 0.0
        domain = [
            ("company_id", "=", company_id),
            ("account_id", "in", account_ids),
            ("move_id.state", "=", "posted" if target_move == "posted" else "draft"),
        ]
        if target_move == "all":
            domain = [d for d in domain if d[0] != "move_id.state"]
            domain.append(("move_id.state", "in", ("draft", "posted")))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        if journal_ids:
            domain.append(("journal_id", "in", journal_ids))
        analytic_ids = set(analytic_account_ids or [])
        if analytic_plan_ids:
            plan_accounts = self.env["account.analytic.account"].search([("plan_id", "in", analytic_plan_ids)]).ids
            analytic_ids.update(plan_accounts)
        if analytic_ids:
            for analytic_id in analytic_ids:
                domain.append(("analytic_distribution", "ilike", f'"{analytic_id}"'))
        groups = self.env["account.move.line"].read_group(domain, ["balance:sum"], [])
        return float(groups[0]["balance"] if groups else 0.0)

    @api.model
    def _build_lines(
        self,
        config,
        company_id,
        target_move,
        date_from=None,
        date_to=None,
        journal_ids=None,
        analytic_plan_ids=None,
        analytic_account_ids=None,
        comparison_date_from=None,
        comparison_date_to=None,
    ):
        if not config:
            raise UserError("Please configure Financial Report lines first.")

        amount_map = {}
        by_code = {line.code: line for line in config.line_ids}
        ordered = config.line_ids.sorted("sequence")

        for line in ordered:
            if line.account_ids:
                amt = self._sum_accounts(
                    line.account_ids.ids,
                    company_id,
                    target_move,
                    date_from,
                    date_to,
                    journal_ids=journal_ids,
                    analytic_plan_ids=analytic_plan_ids,
                    analytic_account_ids=analytic_account_ids,
                )
                cmp_amt = self._sum_accounts(
                    line.account_ids.ids,
                    company_id,
                    target_move,
                    comparison_date_from,
                    comparison_date_to,
                    journal_ids=journal_ids,
                    analytic_plan_ids=analytic_plan_ids,
                    analytic_account_ids=analytic_account_ids,
                )
                if line.sign == "invert":
                    amt *= -1
                    cmp_amt *= -1
                amount_map[line.code] = amt
                amount_map[f"{line.code}__cmp"] = cmp_amt
            else:
                amount_map[line.code] = 0.0
                amount_map[f"{line.code}__cmp"] = 0.0

        # Build hierarchy by parent_code for section total rollups.
        children_map = {}
        for ln in ordered:
            if ln.parent_code:
                children_map.setdefault(ln.parent_code, []).append(ln.code)

        def subtotal_for_section(section_code, comparison=False):
            total = 0.0
            section = by_code.get(section_code)
            if section and not section.is_total:
                key = f"{section_code}__cmp" if comparison else section_code
                total += amount_map.get(key, 0.0)

            for child in children_map.get(section_code, []):
                child_line = by_code.get(child)
                if not child_line:
                    continue
                if child_line.is_total:
                    continue
                total += subtotal_for_section(child, comparison=comparison)
            return total

        for line in ordered:
            if line.is_total:
                # In this setup, total lines are usually leaf nodes with parent_code
                # pointing to the section to total.
                root_code = line.parent_code or line.code
                amount_map[line.code] = subtotal_for_section(root_code, comparison=False)
                amount_map[f"{line.code}__cmp"] = subtotal_for_section(root_code, comparison=True)

        rows = []
        for line in ordered:
            rows.append(
                {
                    "code": line.code,
                    "name": line.name,
                    "level": line.level,
                    "is_total": line.is_total,
                    "amount": amount_map.get(line.code, 0.0),
                    "comparison_amount": amount_map.get(f"{line.code}__cmp", 0.0),
                }
            )
        return rows


class ReportBalanceSheetCustom(models.AbstractModel):
    _name = "report.ft_backend.report_balance_sheet_custom"
    _inherit = "report.ft_backend.financial_statement_mixin"
    _description = "Custom Balance Sheet"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get("form"):
            raise UserError("Form content is missing, this report cannot be printed.")
        form = data["form"]
        company_id = self._as_id(form.get("company_id")) or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        config = self._config("balance_sheet", company_id)
        rows = self._build_lines(
            config,
            company_id,
            form.get("target_move"),
            date_to=form.get("date_to"),
            journal_ids=form.get("journal_ids") or [],
            analytic_plan_ids=form.get("analytic_plan_ids") or [],
            analytic_account_ids=form.get("analytic_account_ids") or [],
            comparison_date_to=form.get("comparison_date_to"),
        )

        return {
            "company": company,
            "title": "Balance Sheet",
            "period_text": f"As at {self._fmt_date(form.get('date_to'))}",
            "currency": company.currency_id.name,
            "comparison_period_text": self._fmt_date(form.get("comparison_date_to")) if form.get("comparison_date_to") else "",
            "filter_summary": {
                "target_move": form.get("target_move"),
                "journals": ", ".join(self.env["account.journal"].browse(form.get("journal_ids") or []).mapped("name")),
                "analytics": ", ".join(self.env["account.analytic.account"].browse(form.get("analytic_account_ids") or []).mapped("name")),
                "analytic_plans": ", ".join(self.env["account.analytic.plan"].browse(form.get("analytic_plan_ids") or []).mapped("name")),
            },
            "rows": rows,
        }


class ReportIncomeStatementCustom(models.AbstractModel):
    _name = "report.ft_backend.report_income_statement_custom"
    _inherit = "report.ft_backend.financial_statement_mixin"
    _description = "Custom Income Statement"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get("form"):
            raise UserError("Form content is missing, this report cannot be printed.")
        form = data["form"]
        company_id = self._as_id(form.get("company_id")) or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        config = self._config("income_statement", company_id)
        rows = self._build_lines(
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

        return {
            "company": company,
            "title": "Income Statement",
            "period_text": f"From {self._fmt_date(form.get('date_from'))} to {self._fmt_date(form.get('date_to'))}",
            "currency": company.currency_id.name,
            "comparison_period_text": (
                f"{self._fmt_date(form.get('comparison_date_from'))} - {self._fmt_date(form.get('comparison_date_to'))}"
                if form.get("comparison_date_from") and form.get("comparison_date_to")
                else ""
            ),
            "filter_summary": {
                "target_move": form.get("target_move"),
                "journals": ", ".join(self.env["account.journal"].browse(form.get("journal_ids") or []).mapped("name")),
                "analytics": ", ".join(self.env["account.analytic.account"].browse(form.get("analytic_account_ids") or []).mapped("name")),
                "analytic_plans": ", ".join(self.env["account.analytic.plan"].browse(form.get("analytic_plan_ids") or []).mapped("name")),
            },
            "rows": rows,
        }
