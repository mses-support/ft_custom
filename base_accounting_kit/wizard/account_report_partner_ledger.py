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
import json
from odoo import fields, models
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class AccountPartnerLedger(models.TransientModel, ReportXlsxMixin):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_report_partner_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_report_partner_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Partner Ledger Report", default="Partner Ledger Report", required=True, translate=True)
    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on report if the "
                                          "currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        help='Leave empty to include all partners/vendors.',
    )

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency,
                             'partner_ids': self.partner_ids.ids})
        return self.env.ref(
            'base_accounting_kit.action_report_partnerledger').report_action(
            self, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.user.lang or 'en_US')
        data = self.pre_print_report(data)
        data['form'].update({
            'reconciled': self.reconciled,
            'amount_currency': self.amount_currency,
            'partner_ids': self.partner_ids.ids,
        })
        report_values = self.env['report.base_accounting_kit.report_partnerledger']._get_report_values(
            [], data={'form': data['form']}
        )
        partner_rows = []
        for partner in report_values['docs']:
            line_items = []
            for line in report_values['lines'](report_values['data'], partner):
                line_items.append({
                    'date': line.get('date'),
                    'code': line.get('code'),
                    'displayed_name': line.get('displayed_name'),
                    'debit': float(line.get('debit', 0.0)),
                    'credit': float(line.get('credit', 0.0)),
                    'progress': float(line.get('progress', 0.0)),
                    'amount_currency': float(line.get('amount_currency', 0.0)),
                    'currency_code': line.get('currency_code'),
                })
            partner_rows.append({
                'ref': partner.ref or '',
                'name': partner.name or '',
                'total_debit': float(report_values['sum_partner'](report_values['data'], partner, 'debit') or 0.0),
                'total_credit': float(report_values['sum_partner'](report_values['data'], partner, 'credit') or 0.0),
                'total_balance': float(report_values['sum_partner'](report_values['data'], partner, 'debit - credit') or 0.0),
                'lines': line_items,
            })
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'target_move': data['form'].get('target_move'),
            'with_currency': data['form'].get('amount_currency'),
            'selected_partners': ', '.join(self.partner_ids.mapped('name')) or 'All',
            'partners': partner_rows,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.report.partner.ledger',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Partner Ledger',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        headers = ['Date', 'JRNL', 'Ref', 'Debit', 'Credit', 'Balance']
        if data.get('with_currency'):
            headers.append('Currency')
        rows = []
        for partner in data.get('partners', []):
            section = [
                f"{partner.get('ref') or ''} - {partner.get('name') or ''}".strip(' -'),
                '',
                '',
                float(partner.get('total_debit', 0.0)),
                float(partner.get('total_credit', 0.0)),
                float(partner.get('total_balance', 0.0)),
            ]
            if data.get('with_currency'):
                section.append('')
            rows.append({'type': 'section', 'values': section})
            for line in partner.get('lines', []):
                vals = [
                    line.get('date') or '',
                    line.get('code') or '',
                    line.get('displayed_name') or '',
                    float(line.get('debit', 0.0)),
                    float(line.get('credit', 0.0)),
                    float(line.get('progress', 0.0)),
                ]
                if data.get('with_currency'):
                    vals.append(
                        ('%s %s' % (
                            line.get('amount_currency', 0.0),
                            line.get('currency_code') or '')).strip()
                    )
                rows.append({'values': vals})
        table = {
            'sheet_name': 'Partner Ledger',
            'title': f"{data.get('company_name', '')}: Partner Ledger",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Date From:', data.get('date_from') or ''),
                ('Date To:', data.get('date_to') or ''),
                ('Selected Partners:', data.get('selected_partners') or 'All'),
            ],
            'headers': headers,
            'column_widths': [(0, 0, 12), (1, 1, 10), (2, 2, 40), (3, 5, 14), (6, 6, 18)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
