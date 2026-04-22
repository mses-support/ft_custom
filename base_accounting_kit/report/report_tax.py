# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportTax(models.AbstractModel):
    _name = 'report.base_accounting_kit.report_tax'
    _description = 'Tax Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        scope = data['form'].get('tax_scope', 'all')
        report_name = {
            'sale': 'Sales Tax Report',
            'purchase': 'Purchase Tax Report',
        }.get(scope, 'Tax Report')
        return {
            'data': data['form'],
            'lines': self.get_lines(data.get('form')),
            'report_name': report_name,
        }

    @api.model
    def _get_company_id(self, options):
        company_value = options.get('company_id')
        if isinstance(company_value, (list, tuple)):
            return company_value[0]
        return company_value or self.env.company.id

    @api.model
    def _get_move_domain(self, options, section):
        move_types = {
            'sale': ('out_invoice', 'out_refund'),
            'purchase': ('in_invoice', 'in_refund'),
        }
        domain = [
            ('company_id', '=', self._get_company_id(options)),
            ('move_type', 'in', move_types[section]),
        ]
        if options.get('target_move') == 'posted':
            domain.append(('state', '=', 'posted'))
        else:
            domain.append(('state', 'in', ('draft', 'posted')))
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        if options.get('date_from'):
            domain.append(('date', '>=', options['date_from']))
        if options.get('date_to'):
            domain.append(('date', '<=', options['date_to']))
        return domain

    @api.model
    def _format_vat_percent(self, tax):
        if tax.amount_type in ('percent', 'division'):
            return f"{tax.amount:g}%"
        return ''

    @api.model
    def _prepare_rows(self, options, section):
        moves = self.env['account.move'].search(
            self._get_move_domain(options, section),
            order='invoice_date asc, date asc, id asc',
        )
        rows = []
        for move in moves:
            tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id and not line.display_type)
            for tax_line in tax_lines:
                tax = tax_line.tax_line_id
                if tax.type_tax_use not in (section, 'none'):
                    continue
                taxable_amount = abs(tax_line.tax_base_amount or 0.0)
                vat_amount = abs(tax_line.balance or 0.0)
                if not taxable_amount and not vat_amount:
                    continue
                line_date = move.invoice_date or move.date
                line_date = fields.Date.to_date(line_date).strftime('%d-%m-%Y') if line_date else ''
                number = move.name if move.name and move.name != '/' else (move.ref or '')
                rows.append({
                    'date': line_date,
                    'number': number,
                    'partner_name': move.partner_id.name or '',
                    'partner_vat': move.partner_id.vat or '',
                    'taxable_amount': taxable_amount,
                    'vat_percent': self._format_vat_percent(tax),
                    'vat_amount': vat_amount,
                    'total_amount': taxable_amount + vat_amount,
                    'tax_code': tax.name or '',
                })
        return rows

    @api.model
    def get_lines(self, options):
        groups = {
            'sale': self._prepare_rows(options, 'sale'),
            'purchase': self._prepare_rows(options, 'purchase'),
        }
        scope = options.get('tax_scope', 'all')
        if scope == 'sale':
            groups['purchase'] = []
        elif scope == 'purchase':
            groups['sale'] = []
        return groups
