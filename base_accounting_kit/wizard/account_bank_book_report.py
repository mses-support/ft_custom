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
import io
import json
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class BankBookWizard(models.TransientModel, ReportXlsxMixin):
    _name = 'account.bank.book.report'
    _description = 'Account Bank Book Report'

    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.company)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')],
                                   string='Target Moves', required=True,
                                   default='posted')
    date_from = fields.Date(string='Start Date', default=date.today(),
                            required=True)
    date_to = fields.Date(string='End Date', default=date.today(),
                          required=True)
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date')
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field allow you to add a '
                                          'row to display the amount of debit/credit/balance that '
                                          'precedes the filter you\'ve set.')

    def _get_default_account_ids(self):
        journals = self.env['account.journal'].search([('type', '=', 'bank')])
        accounts = []
        for journal in journals:
            accounts.append(journal.default_account_id.id)
        return accounts

    account_ids = fields.Many2many('account.account',
                                   'account_report_bankbook_account_rel',
                                   'report_id', 'account_id',
                                   'Accounts',
                                   default=_get_default_account_ids)
    journal_ids = fields.Many2many('account.journal',
                                   'account_report_bankbook_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search([]))

    @api.onchange('account_ids')
    def onchange_account_ids(self):
        if self.account_ids:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = []
            for journal in journals:
                accounts.append(journal.default_account_id.id)
            domain = {'account_ids': [('id', 'in', accounts)]}
            return {'domain': domain}

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
        data = self._prepare_report_data()
        return self.env.ref(
            'base_accounting_kit.action_report_bank_book').report_action(
            self, data=data)

    def _prepare_report_data(self):
        self.ensure_one()
        if self.initial_balance and not self.date_from:
            raise UserError(_("You must choose a Start Date"))
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move',
             'display_account',
             'account_ids', 'sortby', 'initial_balance'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')
        return data

    def _get_accounts_for_report(self, form_data):
        init_balance = form_data.get('initial_balance', True)
        sortby = form_data.get('sortby', 'sort_date')
        display_account = 'movement'
        journal_codes = []
        if form_data.get('journal_ids'):
            journal_codes = [journal.code for journal in
                             self.env['account.journal'].search(
                                 [('id', 'in', form_data['journal_ids'])])]
        account_ids = form_data.get('account_ids')
        accounts = self.env['account.account'].search(
            [('id', 'in', account_ids)])
        if not accounts:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = self.env['account.account'].search(
                [('id', 'in', journals.mapped('default_account_id').ids)])
        accounts_res = self.env[
            'report.base_accounting_kit.report_bank_book'].with_context(
            form_data.get('used_context', {}))._get_account_move_entry(
            accounts, init_balance, sortby, display_account)
        return accounts_res, journal_codes

    def check_report_xlsx(self):
        self.ensure_one()
        data = self._prepare_report_data()
        accounts_res, journal_codes = self._get_accounts_for_report(
            data['form'])
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'target_move': data['form'].get('target_move'),
            'sortby': data['form'].get('sortby'),
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'display_account': data['form'].get('display_account'),
            'print_journal': journal_codes,
            'accounts': accounts_res,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.bank.book.report',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Bank Book Report',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        rows = []
        for account in data.get('accounts', []):
            rows.append({
                'type': 'section',
                'values': [
                    f"{account.get('code', '')} {account.get('name', '')}".strip(),
                    '', '', '', '', '',
                    float(account.get('debit', 0.0)),
                    float(account.get('credit', 0.0)),
                    float(account.get('balance', 0.0)),
                    '',
                ],
            })
            for line in account.get('move_lines', []):
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
            'sheet_name': 'Bank Book',
            'title': f"{data.get('company_name', '')}: Bank Book Report",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Journals:', ', '.join(data.get('print_journal', []))),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Sorted By:', 'Date' if data.get('sortby') == 'sort_date' else 'Journal and Partner'),
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
