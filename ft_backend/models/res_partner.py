from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    name_arabic = fields.Char(string="Name Arabic", required=True)
    street_arabic = fields.Char(string="Street Arabic", required=True)
    street2_arabic = fields.Char(string="Street2 Arabic", required=True)
    city_arabic = fields.Char(string="City Arabic", required=True)
    zip_arabic = fields.Char(string="ZIP Arabic", required=True)
    country_arabic = fields.Char(string="Country Arabic", required=True)
    address_arabic = fields.Text(string="Address Arabic", required=True)
    company_registry_arabic = fields.Char(string="CR No. Arabic", required=True)
    vat_arabic = fields.Char(string="VAT Arabic", required=True)
