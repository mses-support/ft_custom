from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    po_daily_limit = fields.Float(string="PO Daily Approval Limit")
    po_monthly_limit = fields.Float(string="PO Monthly Approval Limit")
    name_arabic = fields.Char(
        string="Name Arabic",
        related="partner_id.name_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    street_arabic = fields.Char(
        string="Street Arabic",
        related="partner_id.street_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    street2_arabic = fields.Char(
        string="Street2 Arabic",
        related="partner_id.street2_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    city_arabic = fields.Char(
        string="City Arabic",
        related="partner_id.city_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    zip_arabic = fields.Char(
        string="ZIP Arabic",
        related="partner_id.zip_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    country_arabic = fields.Char(
        string="Country Arabic",
        related="partner_id.country_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    address_arabic = fields.Text(
        string="Address Arabic",
        related="partner_id.address_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    company_registry_arabic = fields.Char(
        string="CR No. Arabic",
        related="partner_id.company_registry_arabic",
        readonly=False,
        store=True,
        required=True,
    )
    vat_arabic = fields.Char(
        string="VAT Arabic",
        related="partner_id.vat_arabic",
        readonly=False,
        store=True,
        required=True,
    )
