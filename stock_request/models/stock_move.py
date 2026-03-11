# Copyright 2017-2020 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    allocation_ids = fields.One2many(
        comodel_name="stock.request.allocation",
        inverse_name="stock_move_id",
        string="Stock Request Allocation",
    )

    stock_request_ids = fields.One2many(
        comodel_name="stock.request",
        string="Stock Requests",
        compute="_compute_stock_request_ids",
    )
    cost = fields.Float(string="Cost", digits="Product Price", copy=False)
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        check_company=True,
        copy=False,
    )

    @api.depends("allocation_ids")
    def _compute_stock_request_ids(self):
        for rec in self:
            rec.stock_request_ids = rec.allocation_ids.mapped("stock_request_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id") and "cost" not in vals:
                company_id = vals.get("company_id") or self.env.company.id
                product = self.env["product.product"].with_company(company_id).browse(
                    vals["product_id"]
                )
                vals["cost"] = product.standard_price
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "product_id" in vals and "cost" not in vals:
            for move in self:
                move.cost = (
                    move.product_id.with_company(move.company_id).standard_price
                    if move.product_id
                    else 0.0
                )
        return res

    @api.onchange("product_id")
    def _onchange_product_id_set_cost(self):
        for move in self:
            move.cost = (
                move.product_id.with_company(move.company_id).standard_price
                if move.product_id
                else 0.0
            )

    def _merge_moves_fields(self):
        res = super(StockMove, self)._merge_moves_fields()
        res["allocation_ids"] = [(4, m.id) for m in self.mapped("allocation_ids")]
        return res

    @api.constrains("company_id")
    def _check_company_stock_request(self):
        if any(
            self.env["stock.request.allocation"].search(
                [
                    ("company_id", "!=", rec.company_id.id),
                    ("stock_move_id", "=", rec.id),
                ],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "The company of the stock request must match with "
                    "that of the location."
                )
            )

    def copy_data(self, default=None):
        if not default:
            default = {}
        if "allocation_ids" not in default:
            default["allocation_ids"] = []
        for alloc in self.allocation_ids:
            default["allocation_ids"].append(
                (
                    0,
                    0,
                    {
                        "stock_request_id": alloc.stock_request_id.id,
                        "requested_product_uom_qty": alloc.requested_product_uom_qty,
                    },
                )
            )
        return super(StockMove, self).copy_data(default)

    def _action_cancel(self):
        """Apply sudo to prevent requests ACL errors if the user does not have
        permissions (example: productions)."""
        res = super()._action_cancel()
        self.mapped("allocation_ids.stock_request_id").sudo().check_cancel()
        return res

    def _action_done(self, cancel_backorder=False):
        """Apply sudo to prevent requests ACL errors if the user does not have
        permissions (example: productions)."""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        self.mapped("allocation_ids.stock_request_id").sudo().check_done()
        return res
