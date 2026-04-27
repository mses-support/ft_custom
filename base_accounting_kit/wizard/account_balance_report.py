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
from odoo import api, fields, models, _
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class AccountBalanceReport(models.TransientModel, ReportXlsxMixin):
    _name = 'account.balance.report'
    _inherit = "account.common.account.report"
    _description = 'Trial Balance Report'

    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_balance_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_balance_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    name = fields.Char(string="Trial Balance", default="Trial Balance", required=True, translate=True)
    journal_ids = fields.Many2many('account.journal',
                                   'account_balance_report_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=[])

    @api.model
    def _get_report_name(self):
        period_id = self._get_selected_period_id()
        return self.env['consolidation.period'].browse(period_id)['display_name'] or _("Trial Balance")

    def _print_report(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'base_accounting_kit.action_report_trial_balance').report_action(
            records, data=data)

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
        accounts = self.env['account.account'].search([])
        account_res = self.env[
            'report.base_accounting_kit.report_trial_balance'
        ].with_context(data['form'].get('used_context'))._get_accounts(
            accounts, data['form'].get('display_account'))
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'target_move': data['form'].get('target_move'),
            'display_account': data['form'].get('display_account'),
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'accounts': account_res,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.balance.report',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Trial Balance',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        rows = []
        for account in data.get('accounts', []):
            rows.append({
                'values': [
                    account.get('code') or '',
                    account.get('name') or '',
                    float(account.get('opening_debit', 0.0)),
                    float(account.get('opening_credit', 0.0)),
                    float(account.get('debit', 0.0)),
                    float(account.get('credit', 0.0)),
                    float(account.get('balance', 0.0)),
                ],
            })
        table = {
            'sheet_name': 'Trial Balance',
            'title': f"{data.get('company_name', '')}: Trial Balance",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Display Account:', data.get('display_account') or ''),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Date From:', data.get('date_from') or ''),
                ('Date To:', data.get('date_to') or ''),
            ],
            'header_col_count': 7,
            'header_rows': [
                ['Code', 'Account', 'Opening Balance', None, 'Debit', 'Credit', 'Balance'],
                [None, None, 'Debit', 'Credit', None, None, None],
            ],
            'header_merges': [
                (0, 0, 1, 0, 'Code'),
                (0, 1, 1, 1, 'Account'),
                (0, 2, 0, 3, 'Opening Balance'),
                (0, 4, 1, 4, 'Debit'),
                (0, 5, 1, 5, 'Credit'),
                (0, 6, 1, 6, 'Balance'),
            ],
            'column_widths': [(0, 0, 16), (1, 1, 35), (2, 6, 18)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
