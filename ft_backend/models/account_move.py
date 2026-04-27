from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    approval_stage = fields.Selection(
        [("reviewer", "Reviewer"), ("confirmed", "Confirmed")],
        string="Approval Stage",
        default="confirmed",
        required=True,
        copy=False,
    )
    approval_required = fields.Boolean(
        string="Approval Required",
        compute="_compute_approval_required",
        store=False,
    )

    @api.depends("move_type", "journal_id.type")
    def _compute_approval_required(self):
        for move in self:
            move.approval_required = move._is_approval_required_move()

    def _is_approval_required_move(self):
        self.ensure_one()
        return self.move_type in ("out_invoice", "in_invoice") or (
            self.move_type == "entry" and self.journal_id.type == "general"
        )

    def _approval_required_moves(self):
        return self.filtered(lambda move: move._is_approval_required_move())

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        approval_moves = moves._approval_required_moves().filtered(
            lambda move: move.state == "draft" and move.approval_stage != "reviewer"
        )
        if approval_moves:
            approval_moves.write({"approval_stage": "reviewer"})
        return moves

    def button_draft(self):
        res = super().button_draft()
        approval_moves = self._approval_required_moves().filtered(
            lambda move: move.state == "draft" and move.approval_stage != "reviewer"
        )
        if approval_moves:
            approval_moves.write({"approval_stage": "reviewer"})
        return res

    def action_set_reviewer(self):
        moves = self._approval_required_moves().filtered(lambda move: move.state == "draft")
        if not moves:
            return True
        if not self.env.user.has_group("ft_backend.group_move_reviewer"):
            raise AccessError(
                _("Only users in the Invoice/Bill/JE Reviewer group can set stage to Reviewer.")
            )
        moves.write({"approval_stage": "reviewer"})
        return True

    def action_set_confirmed(self):
        moves = self._approval_required_moves().filtered(lambda move: move.state == "draft")
        if not moves:
            return True
        if not self.env.user.has_group("ft_backend.group_move_confirmer"):
            raise AccessError(
                _("Only users in the Invoice/Bill/JE Confirmer group can set stage to Confirmed.")
            )
        pending = moves.filtered(lambda move: move.approval_stage != "reviewer")
        if pending:
            raise UserError(_("Only documents in Reviewer stage can be moved to Confirmed stage."))
        moves.write({"approval_stage": "confirmed"})
        return True

    def action_post(self):
        approval_moves = self._approval_required_moves()
        if approval_moves and not self.env.is_superuser():
            if not self.env.user.has_group("ft_backend.group_move_confirmer"):
                raise AccessError(
                    _(
                        "Only users in the Invoice/Bill/JE Confirmer group can post "
                        "Customer Invoices, Vendor Bills, or Journal Entries."
                    )
                )
            unconfirmed = approval_moves.filtered(lambda move: move.approval_stage != "confirmed")
            if unconfirmed:
                raise UserError(
                    _(
                        "Document must be in Confirmed stage before posting.\n"
                        "Please confirm approval first."
                    )
                )
        return super().action_post()

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(product_line)

        # Invoice product lines should bill as: quantity * rental_days * unit_price.
        if self.is_invoice(include_receipts=True) and product_line.display_type == 'product':
            base_line['quantity'] = product_line.quantity * (product_line.rental_days or 0)

        return base_line
