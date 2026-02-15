from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    rental_days = fields.Integer(string="Rental Days", default=1)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id', 'rental_days')
    def _compute_totals(self):
        super()._compute_totals()
