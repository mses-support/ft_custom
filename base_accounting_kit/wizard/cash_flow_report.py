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
from odoo import api, fields, models
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class AccountingReport(models.TransientModel, ReportXlsxMixin):
    _name = "cash.flow.report"
    _inherit = "account.report"
    _description = "Cash Flow Report"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_cash_flow_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_cash_flow_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Cash Flow Report", default="Cash Flow Report", required=True, translate=True)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]",
    )

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(
                self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search(
                [('name', 'ilike', menu)])
        return reports and reports[0] or False

    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report',
                                        string='Account Reports',
                                        required=True,
                                        default=_get_account_report)
    label_filter = fields.Char(string='Column Label',
                               help="This label will be displayed on report to show the balance"
                                    " computed for the given comparison filter.")
    filter_cmp = fields.Selection(
        [('filter_no', 'No Filters'), ('filter_date', 'Date')],
        string='Filter by', required=True, default='filter_no')
    date_from_cmp = fields.Date(string='Date Start')
    date_to_cmp = fields.Date(string='Date End')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison.")

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
            result['strict_range'] = True
        return result

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        return result

    # @api.multi
    def check_report(self):
        res = super(AccountingReport, self).check_report()
        data = {}
        data['form'] = self.read(
            ['account_report_id', 'date_from_cmp', 'date_to_cmp',
             'journal_ids', 'filter_cmp', 'target_move'])[0]
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, data):
        raise NotImplementedError()

    def _print_report(self, data):
        data['form'].update(self.read(
            ['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
             'account_report_id', 'enable_filter', 'label_filter',
             'target_move'])[0])
        return self.env.ref(
            'base_accounting_kit.action_report_cash_flow').report_action(self,
                                                                         data=data,
                                                                         config=False)

    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        data['form'].update(self.read(
            ['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
             'account_report_id', 'enable_filter', 'label_filter', 'target_move'])[0])
        comparison_context = self._build_comparison_context({'form': data['form']})
        data['form']['comparison_context'] = comparison_context
        report_lines = self.env[
            'report.base_accounting_kit.report_cash_flow'].get_account_lines(data['form'])
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'report_name': data['form']['account_report_id'][1],
            'target_move': data['form'].get('target_move'),
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'debit_credit': data['form'].get('debit_credit'),
            'enable_filter': data['form'].get('enable_filter'),
            'label_filter': data['form'].get('label_filter'),
            'report_lines': report_lines,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'cash.flow.report',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Cash Flow Statement',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        headers = ['Name']
        if data.get('debit_credit'):
            headers.extend(['Debit', 'Credit'])
        headers.append('Balance')
        if data.get('enable_filter'):
            headers.append(data.get('label_filter') or 'Comparison')
        rows = []
        for line in data.get('report_lines', []):
            if line.get('level') == 0:
                continue
            name = '%s%s' % ('  ' * int(line.get('level', 0)), line.get('name', ''))
            vals = [name]
            if data.get('debit_credit'):
                vals.extend([
                    float(line.get('debit', 0.0)),
                    float(line.get('credit', 0.0)),
                ])
            vals.append(float(line.get('balance', 0.0)))
            if data.get('enable_filter'):
                vals.append(float(line.get('balance_cmp', 0.0)))
            rows.append({
                'type': 'section' if int(line.get('level', 0)) <= 3 else 'data',
                'values': vals,
            })
        table = {
            'sheet_name': 'Cash Flow',
            'title': f"{data.get('company_name', '')}: {data.get('report_name', 'Cash Flow Statement')}",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
                ('Date From:', data.get('date_from') or ''),
                ('Date To:', data.get('date_to') or ''),
            ],
            'headers': headers,
            'column_widths': [(0, 0, 44), (1, 5, 18)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
