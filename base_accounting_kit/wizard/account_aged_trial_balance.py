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
import time
import json
from dateutil.relativedelta import relativedelta
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.json import json_default
from .xlsx_mixin import ReportXlsxMixin


class AccountAgedTrialBalance(models.TransientModel, ReportXlsxMixin):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_aged_trail_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_aged_trail_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Account Aged Trial balance Report", default="Account Aged Trial balance Report", required=True, translate=True)

    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True)
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        help='Leave empty to include all partners.',
    )
    period_length = fields.Integer(string='Period Length (days)',
                                   required=True, default=30)
    date_from = fields.Date(required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    date_to = fields.Date(required=True, default=lambda *a: time.strftime('%Y-%m-%d'))

    def _populate_periods(self, form_data):
        period_length = form_data['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not form_data.get('date_from') or not form_data.get('date_to'):
            raise UserError(_('You must set both start date and end date.'))
        start_date = form_data['date_from']
        end_date = form_data['date_to']
        if hasattr(start_date, 'strftime'):
            start_date = start_date.strftime('%Y-%m-%d')
        if hasattr(end_date, 'strftime'):
            end_date = end_date.strftime('%Y-%m-%d')
        if start_date > end_date:
            raise UserError(_('End date must be greater than or equal to start date.'))

        # Keep aging buckets based on end date (as-of date).
        start = form_data['date_to']
        periods = {}
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            periods[str(i)] = {
                'name': (i != 0 and (
                        str((5 - (i + 1)) * period_length) + '-' + str(
                    (5 - i) * period_length)) or (
                                 '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        form_data.update(periods)
        return form_data

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length', 'date_to', 'partner_ids'])[0])
        data['form'] = self._populate_periods(data['form'])
        return self.env.ref(
            'base_accounting_kit.action_report_aged_partner_balance').with_context(
            landscape=True).report_action(self, data=data)

    def _prepare_xlsx_form(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.user.lang or 'en_US')
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length', 'date_to', 'partner_ids'])[0])
        return self._populate_periods(data['form'])

    def check_report_xlsx(self):
        self.ensure_one()
        form_data = self._prepare_xlsx_form()
        report_values = self.env[
            'report.base_accounting_kit.report_agedpartnerbalance'
        ].with_context(
            active_model='account.aged.trial.balance',
            active_id=self.id,
        )._get_report_values([], data={'form': form_data})
        options = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'date_from': form_data.get('date_from'),
            'date_to': form_data.get('date_to'),
            'period_length': form_data.get('period_length'),
            'target_move': form_data.get('target_move'),
            'result_selection': form_data.get('result_selection'),
            'selected_partners': ', '.join(self.env['res.partner'].browse(form_data.get('partner_ids', [])).mapped('name')) or 'All',
            'period_names': [
                form_data['4']['name'], form_data['3']['name'],
                form_data['2']['name'], form_data['1']['name'], form_data['0']['name']
            ],
            'totals': report_values.get('get_direction', []),
            'partners': report_values.get('get_partner_lines', []),
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'account.aged.trial.balance',
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Aged Partner Balance',
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        p = data.get('period_names', ['', '', '', '', ''])
        rows = []
        totals = data.get('totals', [0, 0, 0, 0, 0, 0, 0])
        rows.append({
            'type': 'section',
            'values': [
                'Account Total',
                float(totals[6] if len(totals) > 6 else 0.0),
                float(totals[4] if len(totals) > 4 else 0.0),
                float(totals[3] if len(totals) > 3 else 0.0),
                float(totals[2] if len(totals) > 2 else 0.0),
                float(totals[1] if len(totals) > 1 else 0.0),
                float(totals[0] if len(totals) > 0 else 0.0),
                float(totals[5] if len(totals) > 5 else 0.0),
            ],
        })
        for partner in data.get('partners', []):
            rows.append({
                'values': [
                    partner.get('name') or '',
                    float(partner.get('direction', 0.0)),
                    float(partner.get('4', 0.0)),
                    float(partner.get('3', 0.0)),
                    float(partner.get('2', 0.0)),
                    float(partner.get('1', 0.0)),
                    float(partner.get('0', 0.0)),
                    float(partner.get('total', 0.0)),
                ],
            })
        table = {
            'sheet_name': 'Aged Partner',
            'title': f"{data.get('company_name', '')}: Aged Partner Balance",
            'company_logo': data.get('company_logo'),
            'meta': [
                ('Start Date:', data.get('date_from') or ''),
                ('End Date:', data.get('date_to') or ''),
                ('Period Length (days):', data.get('period_length') or ''),
                ('Partner:', data.get('result_selection') or ''),
                ('Selected Partners:', data.get('selected_partners') or 'All'),
                ('Target Moves:', 'All Entries' if data.get('target_move') == 'all' else 'All Posted Entries'),
            ],
            'headers': ['Partners', 'Not due', p[0], p[1], p[2], p[3], p[4], 'Total'],
            'column_widths': [(0, 0, 32), (1, 7, 16)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
