from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ReportTaxGreen(models.AbstractModel):
    _name = "report.ft_backend.report_tax_green"
    _inherit = "report.base_accounting_kit.report_tax"
    _description = "Tax Detailed Report with Summary"

    _DEFAULT_SUMMARY_ORDER = [
        "Exempt",
        "VAT Zero Rated",
        "VAT 5%",
        "VAT 10%",
        "VAT 15%",
    ]

    @api.model
    def _to_date_string(self, value, date_format="%m/%d/%Y"):
        if not value:
            return ""
        return fields.Date.to_date(value).strftime(date_format)

    @api.model
    def _vat_rate_value(self, tax):
        if tax.amount_type in ("percent", "division"):
            return float(tax.amount or 0.0)
        return 0.0

    @api.model
    def _vat_rate_label(self, rate):
        text = f"{rate:g}"
        return f"VAT {text}%"

    @api.model
    def _vat_type_label(self, tax, rate):
        tax_name = (tax.name or "").lower()
        if "exempt" in tax_name:
            return "Exempt"
        if "zero" in tax_name or abs(rate) < 1e-9:
            return "VAT Zero Rated"
        return self._vat_rate_label(rate)

    @api.model
    def _move_sign(self, move):
        return -1.0 if move.move_type in ("out_refund", "in_refund") else 1.0

    @api.model
    def _collect_detailed_lines(self, options):
        scope = options.get("tax_scope", "all")
        sections = []
        if scope in (False, "all", "sale"):
            sections.append("sale")
        if scope in (False, "all", "purchase"):
            sections.append("purchase")

        details = []
        for section in sections:
            moves = self.env["account.move"].search(
                self._get_move_domain(options, section),
                order="invoice_date asc, date asc, id asc",
            )
            trans_type = "Sales" if section == "sale" else "Purchase"
            for move in moves:
                sign = self._move_sign(move)
                tax_lines = move.line_ids.filtered(
                    lambda line: line.tax_line_id and line.display_type in (False, "tax")
                )
                for tax_line in tax_lines:
                    tax = tax_line.tax_line_id
                    if tax.type_tax_use not in (section, "none"):
                        continue
                    net_amount = sign * abs(tax_line.tax_base_amount or 0.0)
                    tax_amount = sign * abs(tax_line.balance or 0.0)
                    if not net_amount and not tax_amount:
                        continue

                    rate = self._vat_rate_value(tax)
                    details.append({
                        "trans_type": trans_type,
                        "ref": move.name if move.name and move.name != "/" else (move.ref or ""),
                        "date": self._to_date_string(move.invoice_date or move.date),
                        "name": move.partner_id.name or "",
                        "net": net_amount,
                        "rate": rate,
                        "tax": tax_amount,
                        "vat_type": self._vat_type_label(tax, rate),
                    })
        return details

    @api.model
    def _build_summary(self, details):
        summary_map = {
            label: {
                "tax_rate": label,
                "outputs": 0.0,
                "output_tax": 0.0,
                "inputs": 0.0,
                "input_tax": 0.0,
                "net_tax": 0.0,
            }
            for label in self._DEFAULT_SUMMARY_ORDER
        }

        for line in details:
            key = line["vat_type"]
            if key not in summary_map:
                summary_map[key] = {
                    "tax_rate": key,
                    "outputs": 0.0,
                    "output_tax": 0.0,
                    "inputs": 0.0,
                    "input_tax": 0.0,
                    "net_tax": 0.0,
                }
            row = summary_map[key]
            if line["trans_type"] == "Sales":
                row["outputs"] += line["net"]
                row["output_tax"] += line["tax"]
            else:
                row["inputs"] += line["net"]
                row["input_tax"] += line["tax"]

        for row in summary_map.values():
            row["net_tax"] = row["output_tax"] - row["input_tax"]

        ordered_keys = self._DEFAULT_SUMMARY_ORDER + sorted(
            set(summary_map.keys()) - set(self._DEFAULT_SUMMARY_ORDER)
        )
        rows = [summary_map[key] for key in ordered_keys]
        total_payable_or_refund = sum(row["net_tax"] for row in rows)
        return rows, total_payable_or_refund

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get("form"):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        form = data["form"]
        details = self._collect_detailed_lines(form)
        summary_rows, total_payable_or_refund = self._build_summary(details)

        period_text = ""
        if form.get("date_from") or form.get("date_to"):
            period_text = f"{self._to_date_string(form.get('date_from'))} - {self._to_date_string(form.get('date_to'))}"

        return {
            "data": form,
            "detail_lines": details,
            "summary_rows": summary_rows,
            "total_payable_or_refund": total_payable_or_refund,
            "report_name": "Tax Detailed Report with Summary",
            "period_text": period_text,
            "report_type_text": "Detailed Report",
        }
