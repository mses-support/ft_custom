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


class AccountPrintJournal(models.TransientModel, ReportXlsxMixin):
    _name = "account.print.journal"
    _inherit = "account.common.journal.report"
    _description = "Account Print Journal"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_common_print_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_common_print_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Journal Audit", default="Journal Audit", required=True, translate=True)
    sort_selection = fields.Selection(
        [('date', 'Date'), ('move_name', 'Journal Entry Number')],
        'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search(
                                       [('type', 'in', ['sale', 'purchase'])]))

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env.ref(
            'base_accounting_kit.action_report_journal').with_context(
            landscape=True).report_action(self, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.user.lang or 'en_US')
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})

        report_model = self.env['report.base_accounting_kit.report_journal_audit']
        journals = self.env['account.journal'].browse(data['form']['journal_ids'])
        lines_data = []
        for journal in journals:
            entries = []
            for aml in report_model.lines(
                data['form'].get('target_move'),
                [journal.id],
                data['form'].get('sort_selection'),
                {'form': data['form']}
            ):
                entries.append({
                    'move': aml.move_id.name if aml.move_id.name != '/' else ('*%s' % aml.move_id.id),
                    'date': aml.date and str(aml.date) or '',
                    'account': aml.account_id.code or '',
                    'partner': (aml.partner_id.name or '')[:60],
                    'label': (aml.name or '')[:120],
                    'debit': float(aml.debit or 0.0),
                    'credit': float(aml.credit or 0.0),
                    'currency': float(aml.amount_currency or 0.0),
                })
            taxes = report_model._get_taxes({'form': data['form']}, journal)
            tax_rows = []
            for tax, amounts in taxes.items():
                tax_rows.append({
                    'name': tax.name,
                    'base_amount': float(amounts.get('base_amount', 0.0)),
                    'tax_amount': float(amounts.get('tax_amount', 0.0)),
                })
            lines_data.append({
                'name': journal.name,
                'entries': entries,
                'sum_debit': float(report_model._sum_debit({'form': data['form']}, journal) or 0.0),
                'sum_credit': float(report_model._sum_credit({'form': data['form']}, journal) or 0.0),
                'taxes': tax_rows,
            })

        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'target_move': data['form'].get('target_move'),
            'sort_selection': data['form'].get('sort_selection'),
            'with_currency': data['form'].get('amount_currency'),
            'journals': lines_data,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.print.journal',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Journals Audit',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        headers = ['Move', 'Date', 'Account', 'Partner', 'Label', 'Debit', 'Credit']
        if data.get('with_currency'):
            headers.append('Currency')
        rows = []
        for journal in data.get('journals', []):
            section = [journal.get('name') or '', '', '', '', '', '', '']
            if data.get('with_currency'):
                section.append('')
            rows.append({'type': 'section', 'values': section})
            for line in journal.get('entries', []):
                vals = [
                    line.get('move') or '',
                    line.get('date') or '',
                    line.get('account') or '',
                    line.get('partner') or '',
                    line.get('label') or '',
                    float(line.get('debit', 0.0)),
                    float(line.get('credit', 0.0)),
                ]
                if data.get('with_currency'):
                    vals.append(float(line.get('currency', 0.0)))
                rows.append({'values': vals})
            summary = ['Total', '', '', '', '', float(journal.get('sum_debit', 0.0)), float(journal.get('sum_credit', 0.0))]
            if data.get('with_currency'):
                summary.append('')
            rows.append({'type': 'section', 'values': summary})
            for tax in journal.get('taxes', []):
                tax_row = [
                    'Tax Declaration',
                    '',
                    tax.get('name') or '',
                    '',
                    '',
                    float(tax.get('base_amount', 0.0)),
                    float(tax.get('tax_amount', 0.0)),
                ]
                if data.get('with_currency'):
                    tax_row.append('')
                rows.append({'values': tax_row})
        table = {
            'sheet_name': 'Journals Audit',
            'title': f"{data.get('company_name', '')}: Journals Audit",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Entries Sorted By:', 'Date' if data.get('sort_selection') == 'date' else 'Journal Entry Number'),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
            ],
            'headers': headers,
            'column_widths': [(0, 0, 20), (1, 1, 12), (2, 2, 12), (3, 3, 24), (4, 4, 36), (5, 7, 14)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
