from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    name_arabic = fields.Char(string="Name Arabic")
    street_arabic = fields.Char(string="Street Arabic")
    street2_arabic = fields.Char(string="Street2 Arabic")
    city_arabic = fields.Char(string="City Arabic")
    zip_arabic = fields.Char(string="ZIP Arabic")
    country_arabic = fields.Char(string="Country Arabic")
    address_arabic = fields.Text(string="Address Arabic")
    company_registry_arabic = fields.Char(string="CR No. Arabic")
    vat_arabic = fields.Char(string="VAT Arabic")
