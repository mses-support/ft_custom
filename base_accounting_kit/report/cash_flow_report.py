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
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportFinancial(models.AbstractModel):
    _name = 'report.base_accounting_kit.report_cash_flow'
    _description = 'Cash Flow Report'

    def _compute_account_balance(self, accounts):
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)
        if accounts:
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + ', '.join(
                mapping.values()) + \
                      " FROM " + tables + \
                      " WHERE account_id IN %s " \
                      + filters + \
                      " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _get_cash_flow_split_report_ids(self):
        """Return report ids that should show debit-only or credit-only flow."""
        cash_in_xml_ids = (
            'base_accounting_kit.cash_in_from_operation0',
            'base_accounting_kit.cash_in_financial0',
            'base_accounting_kit.cash_in_investing0',
        )
        cash_out_xml_ids = (
            'base_accounting_kit.cash_out_operation1',
            'base_accounting_kit.cash_out_financial1',
            'base_accounting_kit.cash_out_investing1',
        )
        cash_in_ids = {
            rec.id for rec in (
                self.env.ref(xml_id, raise_if_not_found=False)
                for xml_id in cash_in_xml_ids
            ) if rec
        }
        cash_out_ids = {
            rec.id for rec in (
                self.env.ref(xml_id, raise_if_not_found=False)
                for xml_id in cash_out_xml_ids
            ) if rec
        }
        return cash_in_ids, cash_out_ids

    def _compute_report_balance(self, reports):
        res = {}
        fields = ['credit', 'debit', 'balance']
        cash_in_ids, cash_out_ids = self._get_cash_flow_split_report_ids()
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # Use direct accounts, or section accounts for cash in/out split
                account_ids = report.account_ids
                if not account_ids and report.id in (cash_in_ids | cash_out_ids):
                    account_ids = report.parent_id.account_ids
                res[report.id]['account'] = self._compute_account_balance(
                    account_ids)
                for value in res[report.id]['account'].values():
                    if report.id in cash_in_ids:
                        debit_value = value.get('debit', 0.0)
                        res[report.id]['debit'] += debit_value
                        res[report.id]['balance'] += debit_value
                        value['credit'] = 0.0
                        value['balance'] = debit_value
                    elif report.id in cash_out_ids:
                        credit_value = value.get('credit', 0.0)
                        res[report.id]['credit'] += credit_value
                        res[report.id]['balance'] -= credit_value
                        value['debit'] = 0.0
                        value['balance'] = -credit_value
                    else:
                        for field in fields:
                            res[report.id][field] += value.get(field, 0.0)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account']
                if report.account_type_ids:
                    accounts = self.env['account.account'].search(
                        [('account_type', '=', report.account_type_ids)])
                res[report.id]['account'] = self._compute_account_balance(
                    accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for value in res2.values():
                    for field in fields:
                        res[report.id][field] += value.get(field)

            elif report.type == 'sum':
                # it's the sum of children; if no child, fallback to linked accounts
                if report.children_ids:
                    res2 = self._compute_report_balance(report.children_ids)
                    for value in res2.values():
                        for field in fields:
                            res[report.id][field] += value.get(field)
                elif report.account_ids:
                    res[report.id]['account'] = self._compute_account_balance(
                        report.account_ids)
                    for value in res[report.id]['account'].values():
                        for field in fields:
                            res[report.id][field] += value.get(field)
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(
            data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(
                data.get('comparison_context'))._compute_report_balance(
                child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get(
                            'account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * int(report.sign),
                'type': 'report',
                'level': bool(report.style_overwrite) and int(
                    report.style_overwrite) or report.level,
                'account_type': report.type or False,
                # used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * int(
                    report.sign)

            lines.append(vals)
            if report.display_detail == 'no_detail':
                # the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if res[report.id].get('account'):
                # if res[report.id].get('debit'):
                sub_lines = []
                company_currency = self.env.company.currency_id
                for account_id, value in res[report.id]['account'].items():
                    # if there are accounts to display, we add them to the
                    # lines with a level equals to their level in
                    # the COA + 1 (to avoid having them with a too low level
                    # that would conflicts with the level of data
                    # financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * int(report.sign) or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.account_type,
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not company_currency.is_zero(
                                vals[
                                    'debit']) or not company_currency.is_zero(
                            vals['credit']):
                            flag = True
                    if not company_currency.is_zero(
                            vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * int(
                            report.sign)
                        if not company_currency.is_zero(
                                vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines,
                                key=lambda sub_line: sub_line['name'])
        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get(
                'active_model') or not self.env.context.get('active_id'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        report_lines = self.get_account_lines(data.get('form'))
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_account_lines': report_lines,
        }
