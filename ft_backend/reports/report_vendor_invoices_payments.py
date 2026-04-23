from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError


class ReportVendorInvoicesPayments(models.AbstractModel):
    _name = "report.ft_backend.report_vendor_invoices_payments"
    _description = "Vendor Invoices & Payments"

    @api.model
    def _to_date_string(self, value):
        if not value:
            return ""
        return fields.Date.to_date(value).strftime("%m/%d/%Y")

    @api.model
    def _as_id(self, value):
        if isinstance(value, (list, tuple)):
            return value[0]
        return value

    @api.model
    def _invoice_domain(self, options):
        domain = [
            ("company_id", "=", self._as_id(options.get("company_id")) or self.env.company.id),
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("date", ">=", options.get("date_from")),
            ("date", "<=", options.get("date_to")),
        ]
        if options.get("target_move") == "posted":
            domain.append(("state", "=", "posted"))
        else:
            domain.append(("state", "in", ("draft", "posted")))
        if options.get("partner_ids"):
            domain.append(("partner_id", "in", options["partner_ids"]))
        return domain

    @api.model
    def _payment_move_domain(self, options):
        domain = [
            ("company_id", "=", self._as_id(options.get("company_id")) or self.env.company.id),
            ("date", ">=", options.get("date_from")),
            ("date", "<=", options.get("date_to")),
            ("move_type", "=", "entry"),
        ]
        if options.get("target_move") == "posted":
            domain.append(("state", "=", "posted"))
        else:
            domain.append(("state", "in", ("draft", "posted")))
        return domain

    @api.model
    def _signed_invoice_amount(self, move):
        amount = abs(float(move.amount_total_signed or 0.0))
        return amount if move.move_type == "in_invoice" else -amount

    @api.model
    def _signed_invoice_balance(self, move):
        balance = abs(float(move.amount_residual_signed or 0.0))
        return balance if move.move_type == "in_invoice" else -balance

    @api.model
    def _allocated_amount_from_line(self, line):
        allocated = 0.0
        partials = line.matched_debit_ids | line.matched_credit_ids
        for partial in partials:
            counterpart = partial.debit_move_id if partial.credit_move_id == line else partial.credit_move_id
            if counterpart.move_id.move_type in ("in_invoice", "in_refund"):
                allocated += float(partial.amount or 0.0)
        sign = 1.0 if line.balance > 0 else -1.0
        return sign * allocated

    @api.model
    def _invoice_rows(self, options):
        rows = []
        moves = self.env["account.move"].search(
            self._invoice_domain(options),
            order="partner_id, invoice_date asc, date asc, id asc",
        )
        for move in moves:
            rows.append(
                {
                    "row_type": "line",
                    "partner_id": move.partner_id.id,
                    "vendor_name": move.partner_id.name or "",
                    "trans_type": "Vendor Bill" if move.move_type == "in_invoice" else "Vendor Credit Note",
                    "reference": move.name if move.name and move.name != "/" else (move.ref or ""),
                    "date": self._to_date_string(move.invoice_date or move.date),
                    "due_date": self._to_date_string(move.invoice_date_due),
                    "payments": 0.0,
                    "invoices": self._signed_invoice_amount(move),
                    "allocated": 0.0,
                    "balance": self._signed_invoice_balance(move),
                    "sort_date": move.invoice_date or move.date or fields.Date.today(),
                    "sort_seq": 1,
                }
            )
        return rows

    @api.model
    def _payment_rows(self, options):
        rows = []
        partner_filter = set(options.get("partner_ids") or [])
        moves = self.env["account.move"].search(
            self._payment_move_domain(options),
            order="date asc, id asc",
        )
        for move in moves:
            payable_lines = move.line_ids.filtered(
                lambda line: line.account_id.account_type == "liability_payable" and line.partner_id
            )
            for line in payable_lines:
                if partner_filter and line.partner_id.id not in partner_filter:
                    continue
                payments = float(line.balance or 0.0)
                allocated = self._allocated_amount_from_line(line)
                if not payments and not allocated:
                    continue
                rows.append(
                    {
                        "row_type": "line",
                        "partner_id": line.partner_id.id,
                        "vendor_name": line.partner_id.name or "",
                        "trans_type": "Payment" if payments >= 0 else "Receipt",
                        "reference": move.name or move.ref or "",
                        "date": self._to_date_string(move.date),
                        "due_date": "",
                        "payments": payments,
                        "invoices": 0.0,
                        "allocated": allocated,
                        "balance": payments - allocated,
                        "sort_date": move.date or fields.Date.today(),
                        "sort_seq": 2,
                    }
                )
        return rows

    @api.model
    def _build_rows(self, options):
        lines = self._invoice_rows(options) + self._payment_rows(options)
        grouped = defaultdict(list)
        for line in lines:
            grouped[line["partner_id"]].append(line)

        result_rows = []
        grand = {"payments": 0.0, "invoices": 0.0, "allocated": 0.0, "balance": 0.0}
        partners = self.env["res.partner"].browse(grouped.keys()).sorted(lambda p: p.name or "")

        for partner in partners:
            partner_lines = sorted(
                grouped[partner.id], key=lambda row: (row["sort_date"], row["sort_seq"], row["reference"])
            )
            for row in partner_lines:
                result_rows.append(row)
                grand["payments"] += row["payments"]
                grand["invoices"] += row["invoices"]
                grand["allocated"] += row["allocated"]
                grand["balance"] += row["balance"]

        return result_rows, grand

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get("form"):
            raise UserError("Form content is missing, this report cannot be printed.")

        form = data["form"]
        rows, grand = self._build_rows(form)
        return {
            "data": form,
            "report_name": "Vendor Invoices & Payments",
            "period_text": f"{self._to_date_string(form.get('date_from'))} - {self._to_date_string(form.get('date_to'))}",
            "currency_text": (
                form["currency_id"][1]
                if isinstance(form.get("currency_id"), (list, tuple)) and len(form["currency_id"]) > 1
                else self.env.company.currency_id.name
            ),
            "rows": rows,
            "grand_total": grand,
        }
