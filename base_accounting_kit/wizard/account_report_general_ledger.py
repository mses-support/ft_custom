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
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.json import json_default
from odoo.tools.misc import get_lang
from .xlsx_mixin import ReportXlsxMixin


class AccountReportGeneralLedger(models.TransientModel, ReportXlsxMixin):
    _name = "account.report.general.ledger"
    _inherit = "account.common.account.report"
    _description = "General Ledger Report"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_report_general_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_report_general_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="General Ledger", default="General Ledger", required=True, translate=True)
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field '
                                          'allow you to add a row to display '
                                          'the amount of debit/credit/balance '
                                          'that precedes the filter you\'ve '
                                          'set.')
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date')
    journal_ids = fields.Many2many('account.journal',
                                   'account_report_general_ledger_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True)
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Leave empty to include all analytic accounts.',
    )
    analytic_plan_ids = fields.Many2many(
        'account.analytic.plan',
        string='Analytic Plans',
        help='Leave empty to include all analytic plans.',
    )

    def _build_contexts(self, data):
        result = super()._build_contexts(data)
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids') or []
        result['analytic_plan_ids'] = data['form'].get('analytic_plan_ids') or []
        return result

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([
            'date_from', 'date_to', 'journal_ids', 'target_move', 'company_id',
            'analytic_account_ids', 'analytic_plan_ids',
        ])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get(
                'date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'base_accounting_kit.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id',
             'analytic_account_ids', 'analytic_plan_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.user.lang or 'en_US')
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        codes = []
        if data['form'].get('journal_ids'):
            codes = [journal.code for journal in self.env['account.journal'].search(
                [('id', 'in', data['form']['journal_ids'])])]
        accounts_res = self.env[
            'report.base_accounting_kit.report_general_ledger'
        ].with_context(data['form'].get('used_context', {}))._get_account_move_entry(
            self.env['account.account'].search([]),
            data['form'].get('initial_balance', True),
            data['form'].get('sortby', 'sort_date'),
            data['form'].get('display_account'),
        )
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'target_move': data['form'].get('target_move'),
            'sortby': data['form'].get('sortby'),
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'display_account': data['form'].get('display_account'),
            'print_journal': codes,
            'analytic_accounts': ', '.join(self.analytic_account_ids.mapped('name')) or 'All',
            'analytic_plans': ', '.join(self.analytic_plan_ids.mapped('name')) or 'All',
            'accounts': accounts_res,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.report.general.ledger',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'General Ledger',
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
            'sheet_name': 'General Ledger',
            'title': f"{data.get('company_name', '')}: General Ledger",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Journals:', ', '.join(data.get('print_journal', []))),
                ('Display Account:', data.get('display_account') or ''),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Sorted By:', 'Date' if data.get('sortby') == 'sort_date' else 'Journal and Partner'),
                ('Date From:', data.get('date_from') or ''),
                ('Date To:', data.get('date_to') or ''),
                ('Analytic Accounts:', data.get('analytic_accounts') or 'All'),
                ('Analytic Plans:', data.get('analytic_plans') or 'All'),
            ],
            'headers': ['Date', 'JRNL', 'Partner', 'Ref', 'Move', 'Entry Label', 'Debit', 'Credit', 'Balance', 'Currency'],
            'column_widths': [
                (0, 0, 12), (1, 1, 10), (2, 2, 22), (3, 3, 20),
                (4, 4, 20), (5, 5, 32), (6, 8, 14), (9, 9, 18),
            ],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
