from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(product_line)

        # Invoice product lines should bill as: quantity * rental_days * unit_price.
        if self.is_invoice(include_receipts=True) and product_line.display_type == 'product':
            base_line['quantity'] = product_line.quantity * (product_line.rental_days or 0)

        return base_line
