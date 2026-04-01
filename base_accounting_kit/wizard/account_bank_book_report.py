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


class BankBookWizard(models.TransientModel):
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
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Bank Book')

        title_format = workbook.add_format({
            'bold': True, 'align': 'center', 'font_size': 14
        })
        label_format = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'border': 1
        })
        text_format = workbook.add_format({'border': 1})
        amount_format = workbook.add_format({
            'border': 1, 'align': 'right', 'num_format': '#,##0.00'
        })
        account_line_format = workbook.add_format({
            'bold': True, 'border': 1
        })
        account_amount_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'right',
            'num_format': '#,##0.00'
        })

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 10)
        sheet.set_column(2, 2, 22)
        sheet.set_column(3, 3, 20)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 28)
        sheet.set_column(6, 8, 14)
        sheet.set_column(9, 9, 18)

        row = 0
        sheet.merge_range(
            row, 0, row, 9,
            f"{data.get('company_name', '')}: Bank Book Report",
            title_format
        )
        row += 2

        sheet.write(row, 0, 'Journals:', label_format)
        sheet.write(row, 1, ', '.join(data.get('print_journal', [])))
        row += 1
        sheet.write(row, 0, 'Target Moves:', label_format)
        sheet.write(row, 1, 'All Entries' if data.get(
            'target_move') == 'all' else 'All Posted Entries')
        row += 1
        sheet.write(row, 0, 'Sorted By:', label_format)
        sheet.write(row, 1, 'Date' if data.get(
            'sortby') == 'sort_date' else 'Journal and Partner')
        row += 1
        if data.get('date_from'):
            sheet.write(row, 0, 'Date From:', label_format)
            sheet.write(row, 1, data.get('date_from'))
            row += 1
        if data.get('date_to'):
            sheet.write(row, 0, 'Date To:', label_format)
            sheet.write(row, 1, data.get('date_to'))
            row += 1

        row += 1
        headers = [
            'Date', 'JRNL', 'Partner', 'Ref', 'Move', 'Entry Label',
            'Debit', 'Credit', 'Balance', 'Currency'
        ]
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_format)
        row += 1

        for account in data.get('accounts', []):
            account_name = f"{account.get('code', '')} {account.get('name', '')}"
            sheet.write(row, 0, account_name.strip(), account_line_format)
            for col in range(1, 6):
                sheet.write(row, col, '', account_line_format)
            sheet.write_number(
                row, 6, float(account.get('debit', 0.0)), account_amount_format)
            sheet.write_number(
                row, 7, float(account.get('credit', 0.0)), account_amount_format)
            sheet.write_number(
                row, 8, float(account.get('balance', 0.0)),
                account_amount_format)
            sheet.write(row, 9, '', account_line_format)
            row += 1

            for line in account.get('move_lines', []):
                sheet.write(row, 0, line.get('ldate') or '', text_format)
                sheet.write(row, 1, line.get('lcode') or '', text_format)
                sheet.write(row, 2, line.get('partner_name') or '', text_format)
                sheet.write(row, 3, line.get('lref') or '', text_format)
                sheet.write(row, 4, line.get('move_name') or '', text_format)
                sheet.write(row, 5, line.get('lname') or '', text_format)
                sheet.write_number(
                    row, 6, float(line.get('debit', 0.0)), amount_format)
                sheet.write_number(
                    row, 7, float(line.get('credit', 0.0)), amount_format)
                sheet.write_number(
                    row, 8, float(line.get('balance', 0.0)), amount_format)
                currency_value = ''
                if line.get('amount_currency') and line.get('amount_currency') > 0.0:
                    currency_value = '%s %s' % (
                        line.get('amount_currency'), line.get('currency_code') or ''
                    )
                sheet.write(row, 9, currency_value, text_format)
                row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
