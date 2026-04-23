from odoo import api, fields, models
from odoo.exceptions import ValidationError


class VendorInvoicesPaymentsReport(models.TransientModel):
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

    def action_print(self):
        self.ensure_one()
        data = {
            "form": self.read(
                ["company_id", "currency_id", "date_from", "date_to", "target_move", "partner_ids"]
            )[0]
        }
        return self.env.ref("ft_backend.action_report_vendor_invoices_payments").report_action(
            self, data=data
        )
