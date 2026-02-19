
import base64
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    zatca_sar_currency_id = fields.Many2one(
        'res.currency',
        string="ZATCA SAR Currency",
        compute="_compute_zatca_sar",
    )
    zatca_total_sar = fields.Monetary(
        string="Total SAR",
        currency_field='zatca_sar_currency_id',
        compute="_compute_zatca_sar",
    )
    zatca_tax_sar = fields.Monetary(
        string="Tax SAR",
        currency_field='zatca_sar_currency_id',
        compute="_compute_zatca_sar",
    )

    def _get_zatca_sar_currency(self):
        self.ensure_one()
        sar_currency = self.env.ref('base.SAR', raise_if_not_found=False)
        if not sar_currency:
            sar_currency = self.env['res.currency'].search([('name', '=', 'SAR')], limit=1)
        return sar_currency or self.company_currency_id

    def _convert_to_sar_currency(self, amount, date):
        self.ensure_one()
        sar_currency = self._get_zatca_sar_currency()
        invoice_currency = self.currency_id or self.company_currency_id
        if invoice_currency == sar_currency:
            return sar_currency.round(amount)
        return sar_currency.round(
            invoice_currency._convert(amount, sar_currency, self.company_id, date)
        )

    @api.depends('amount_total', 'amount_tax', 'currency_id', 'invoice_date', 'date', 'company_id')
    def _compute_zatca_sar(self):
        for move in self:
            date = move.invoice_date or move.date or fields.Date.context_today(move)
            move.zatca_sar_currency_id = move._get_zatca_sar_currency()
            move.zatca_total_sar = move._convert_to_sar_currency(move.amount_total, date)
            move.zatca_tax_sar = move._convert_to_sar_currency(move.amount_tax, date)

    def action_generate_zatca_xml(self):
        self.ensure_one()
        xml_content = self.env['ir.qweb']._render('ft_zatca_custom.zatca_invoice_xml', {'o': self})
        if not xml_content:
            raise UserError("Failed to generate ZATCA XML")
        xml_bytes = xml_content if isinstance(xml_content, bytes) else xml_content.encode('utf-8')
        name = f"ZATCA_{self.name or self.id}.xml"
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'type': 'binary',
            'mimetype': 'application/xml',
            'datas': base64.b64encode(xml_bytes).decode('utf-8'),
            'res_model': 'account.move',
            'res_id': self.id,
        })
        self.message_post(body="ZATCA XML generated.", attachment_ids=[attachment.id])
        return True
