from odoo import api, fields, models
from odoo.addons.base_accounting_kit.wizard.xlsx_mixin import ReportXlsxMixin
from odoo.exceptions import ValidationError


class VendorInvoicesPaymentsReport(models.TransientModel, ReportXlsxMixin):
    _name = "vendor.invoices.payments.report"
    _description = "Vendor Invoices & Payments Report"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
        required=True,
        default="posted",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Vendors",
        domain="[('supplier_rank', '>', 0)]",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("Date From must be before or equal to Date To.")

    def _form_data(self):
        self.ensure_one()
        return self.read(
            ["company_id", "currency_id", "date_from", "date_to", "target_move", "partner_ids"]
        )[0]

    def action_print(self):
        data = {"form": self._form_data()}
        return self.env.ref("ft_backend.action_report_vendor_invoices_payments").report_action(
            self, data=data
        )

    def check_report_xlsx(self):
        form = self._form_data()
        report_model = self.env["report.ft_backend.report_vendor_invoices_payments"]
        rows, grand = report_model._build_rows(form)
        company = self.env["res.company"].browse(
            report_model._as_id(form.get("company_id")) or self.env.company.id
        )
        options = {
            "company_name": company.name or "",
            "company_logo": company.logo,
            "period_text": (
                f"{report_model._to_date_string(form.get('date_from'))} - "
                f"{report_model._to_date_string(form.get('date_to'))}"
            ),
            "currency_text": (
                form["currency_id"][1]
                if isinstance(form.get("currency_id"), (list, tuple)) and len(form["currency_id"]) > 1
                else company.currency_id.name
            ),
            "rows": rows,
            "grand_total": grand,
        }
        return self._xlsx_action(
            "vendor.invoices.payments.report",
            "Vendor Invoices & Payments",
            options,
        )

    def get_xlsx_report(self, data, response):
        xlsx_rows = []
        for row in data.get("rows", []):
            xlsx_rows.append(
                {
                    "values": [
                        row.get("vendor_name", ""),
                        row.get("trans_type", ""),
                        row.get("reference", ""),
                        row.get("date", ""),
                        row.get("due_date", ""),
                        float(row.get("payments", 0.0)),
                        float(row.get("invoices", 0.0)),
                        float(row.get("allocated", 0.0)),
                        float(row.get("balance", 0.0)),
                    ]
                }
            )

        grand = data.get("grand_total", {})
        xlsx_rows.append(
            {
                "type": "section",
                "values": [
                    "Grand Total",
                    "",
                    "",
                    "",
                    "",
                    float(grand.get("payments", 0.0)),
                    float(grand.get("invoices", 0.0)),
                    float(grand.get("allocated", 0.0)),
                    float(grand.get("balance", 0.0)),
                ],
            }
        )

        table = {
            "sheet_name": "Vendor Inv & Pay",
            "title": f"{data.get('company_name', '')}: Vendor Invoices & Payments",
            "company_logo": data.get("company_logo"),
            "meta": [
                ("Period:", data.get("period_text")),
                ("Currency:", data.get("currency_text")),
            ],
            "headers": [
                "Vendor Name",
                "Trans Type",
                "Reference",
                "Date",
                "Due Date",
                "Payments",
                "Invoices",
                "Allocated",
                "Balance",
            ],
            "column_widths": [
                (0, 0, 26),
                (1, 1, 16),
                (2, 2, 20),
                (3, 4, 12),
                (5, 8, 14),
            ],
            "rows": xlsx_rows,
        }
        self._render_xlsx_table(table, response)
