from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    vat_arabic = fields.Char(string="VAT Arabic")
