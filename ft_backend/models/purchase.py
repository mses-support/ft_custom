from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _default_delivery_address_id(self):
        prefix = "ELDA8353"
        partner = self.env["res.partner"].search([
            "|",
            ("name", "=ilike", f"{prefix}%"),
            ("ref", "=ilike", f"{prefix}%"),
        ], limit=1)
        return partner.id

    state = fields.Selection(selection_add=[
        ('to_approve_lvl1', 'Waiting Level 1 Approval'),
        ('to_approve_lvl2', 'Waiting Level 2 Approval'),
    ])

    need_second_level = fields.Boolean(compute="_compute_need_second_level", store=True)

    lvl1_approved = fields.Boolean(default=False)
    lvl2_approved = fields.Boolean(default=False)
    delivery_address_id = fields.Many2one(
        "res.partner",
        required=True,
        string="Delivery Address",
        default=_default_delivery_address_id,
    )

    # ------------------------------------------------
    # Rules
    # ------------------------------------------------
    @api.depends('amount_total', 'user_id', 'company_id')
    def _compute_need_second_level(self):
        for order in self:
            need = False
            company = order.company_id

            daily_limit = company.po_daily_limit or 0.0
            monthly_limit = company.po_monthly_limit or 0.0

            today = date.today()
            first_day = today.replace(day=1)
            next_month = first_day + relativedelta(months=1)

            # ---- DAILY ----
            if daily_limit > 0 and order.user_id:
                daily_domain = [
                    ('id', '!=', order.id),
                    ('user_id', '=', order.user_id.id),
                    ('state', 'in', ['purchase', 'done']),
                    ('date_order', '>=', today),
                    ('date_order', '<', today + relativedelta(days=1)),
                ]
                daily_total = sum(self.search(daily_domain).mapped('amount_total'))
                if daily_total + order.amount_total > daily_limit:
                    need = True

            # ---- MONTHLY ----
            if monthly_limit > 0 and order.user_id:
                monthly_domain = [
                    ('id', '!=', order.id),
                    ('user_id', '=', order.user_id.id),
                    ('state', 'in', ['purchase', 'done']),
                    ('date_order', '>=', first_day),
                    ('date_order', '<', next_month),
                ]
                monthly_total = sum(self.search(monthly_domain).mapped('amount_total'))
                if monthly_total + order.amount_total > monthly_limit:
                    need = True

            order.need_second_level = need

    # ------------------------------------------------
    # Submit
    # ------------------------------------------------
    def action_submit_for_approval(self):
        self.write({'state': 'to_approve_lvl1'})
        return True

    # ------------------------------------------------
    # Level 1
    # ------------------------------------------------
    def action_approve_level1(self):
        for order in self:
            order.lvl1_approved = True
            if order.need_second_level:
                order.state = 'to_approve_lvl2'
            else:
                order.state = 'sent'
                order.button_confirm()   # ✅ CONFIRM
        return True

    # ------------------------------------------------
    # Level 2
    # ------------------------------------------------
    def action_approve_level2(self):
        for order in self:
            order.lvl2_approved = True
            order.state = 'sent'
            order.button_confirm()   # ✅ CONFIRM
        return True





