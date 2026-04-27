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
from datetime import date
import json
from odoo import fields, models
from datetime import datetime, timedelta
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class DayBookWizard(models.TransientModel, ReportXlsxMixin):
    _name = 'account.day.book.report'
    _description = 'Account Day Book Report'

    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.company)
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search([]))
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')], string='Target Moves', required=True,
                                   default='posted')

    account_ids = fields.Many2many('account.account',
                                   'account_report_daybook_account_rel',
                                   'report_id', 'account_id',
                                   'Accounts')

    date_from = fields.Date(string='Start Date', default=date.today(),
                            required=True)
    date_to = fields.Date(string='End Date', default=date.today(),
                          required=True)

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        return result

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = \
        self.read(['date_from', 'date_to', 'journal_ids', 'target_move',
                   'account_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')
        return self.env.ref(
            'base_accounting_kit.day_book_pdf_report').report_action(self,
                                                                     data=data)

    def _prepare_report_data(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move', 'account_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(
            used_context, lang=self.env.context.get('lang') or 'en_US')
        return data

    def _get_records_for_report(self, form_data):
        journal_codes = []
        if form_data.get('journal_ids'):
            journal_codes = [journal.code for journal in
                             self.env['account.journal'].search(
                                 [('id', 'in', form_data['journal_ids'])])]
        active_acc = form_data.get('account_ids') or []
        accounts = self.env['account.account'].search(
            [('id', 'in', active_acc)]) if active_acc else self.env['account.account'].search([])

        date_from_val = form_data.get('date_from')
        date_to_val = form_data.get('date_to')
        if hasattr(date_from_val, 'strftime'):
            date_start = date_from_val
        else:
            date_start = datetime.strptime(date_from_val, '%Y-%m-%d').date()
        if hasattr(date_to_val, 'strftime'):
            date_end = date_to_val
        else:
            date_end = datetime.strptime(date_to_val, '%Y-%m-%d').date()
        days = date_end - date_start
        records = []
        report_model = self.env['report.base_accounting_kit.day_book_report_template']
        for i in range(days.days + 1):
            pass_date = str(date_start + timedelta(days=i))
            accounts_res = report_model.with_context(
                form_data.get('used_context', {}))._get_account_move_entry(
                accounts, form_data, pass_date)
            if accounts_res['lines']:
                records.append({
                    'date': pass_date,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'child_lines': accounts_res['lines'],
                })
        return records, journal_codes

    def check_report_xlsx(self):
        self.ensure_one()
        data = self._prepare_report_data()
        records, journal_codes = self._get_records_for_report(data['form'])
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'target_move': data['form'].get('target_move'),
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'print_journal': journal_codes,
            'records': records,
        }
        return self._xlsx_action(
            'account.day.book.report', 'Day Book Report', options)

    def get_xlsx_report(self, data, response):
        rows = []
        for day in data.get('records', []):
            rows.append({
                'type': 'section',
                'values': [
                    day.get('date') or '',
                    '', '', '', '', '',
                    float(day.get('debit', 0.0)),
                    float(day.get('credit', 0.0)),
                    float(day.get('balance', 0.0)),
                    '',
                ],
            })
            for line in day.get('child_lines', []):
                currency_value = ''
                if line.get('amount_currency') and line.get('amount_currency') > 0.0:
                    currency_value = '%s %s' % (
                        line.get('amount_currency'),
                        line.get('currency_code') or ''
                    )
                rows.append({
                    'values': [
                        line.get('ldate') or '',
                        line.get('lcode') or '',
                        line.get('partner_name') or '',
                        line.get('lref') or '',
                        line.get('move_name') or '',
                        line.get('lname') or '',
                        float(line.get('debit', 0.0)),
                        float(line.get('credit', 0.0)),
                        float(line.get('balance', 0.0)),
                        currency_value,
                    ],
                })

        table = {
            'sheet_name': 'Day Book',
            'title': f"{data.get('company_name', '')}: Day Book Report",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Journals:', ', '.join(data.get('print_journal', []))),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Date From:', data.get('date_from') or ''),
                ('Date To:', data.get('date_to') or ''),
            ],
            'headers': ['Date', 'JRNL', 'Partner', 'Ref', 'Move', 'Entry Label', 'Debit', 'Credit', 'Balance', 'Currency'],
            'column_widths': [
                (0, 0, 12), (1, 1, 10), (2, 2, 22), (3, 3, 20),
                (4, 4, 20), (5, 5, 32), (6, 8, 14), (9, 9, 18),
            ],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
