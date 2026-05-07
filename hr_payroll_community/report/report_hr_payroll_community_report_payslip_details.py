# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
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
from odoo import api, models


class ReportHrPayrollCommunityReportPayslipDetails(models.AbstractModel):
    """Create new model for getting Payslip Details Report"""
    _name = 'report.hr_payroll_community.report_payslipdetails'
    _description = 'Payslip Details Report'

    def get_details_by_rule_category(self, payslip_lines):
        """Function for get Salary Rule Categories"""
        res = {}
        if not payslip_lines:
            return res

        # Aggregate totals by salary rule category (including parent
        # categories) and render each category only once.
        for line in payslip_lines.sorted(key=lambda l: (l.slip_id.id, l.sequence, l.id)):
            if not line.category_id:
                continue
            slip_id = line.slip_id.id
            res.setdefault(slip_id, [])
            category_index = {row['category_id']: row for row in res[slip_id]}

            chain = []
            category = line.category_id
            while category:
                chain.append(category)
                category = category.parent_id
            chain.reverse()  # Root -> leaf for stable display order.

            for level, category in enumerate(chain):
                row = category_index.get(category.id)
                if not row:
                    row = {
                        'category_id': category.id,
                        'rule_category': category.name,
                        'name': category.name,
                        'code': category.code,
                        'level': level,
                        'total': 0.0,
                    }
                    res[slip_id].append(row)
                    category_index[category.id] = row
                row['total'] += line.total

        return res

    def get_lines_by_contribution_register(self, payslip_lines):
        """Function for getting Contribution Register Lines"""
        result = {}
        res = {}
        for line in payslip_lines.filtered('register_id'):
            result.setdefault(line.slip_id.id, {})
            result[line.slip_id.id].setdefault(line.register_id, line)
            result[line.slip_id.id][line.register_id] |= line
        for payslip_id, lines_dict in result.items():
            res.setdefault(payslip_id, [])
            for register, lines in lines_dict.items():
                res[payslip_id].append({
                    'register_name': register.name,
                    'total': sum(lines.mapped('total')),
                })
                for line in lines:
                    res[payslip_id].append({
                        'name': line.name,
                        'code': line.code,
                        'quantity': line.quantity,
                        'amount': line.amount,
                        'total': line.total,
                    })
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Function for getting Payslip Details Report values"""
        payslips = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'get_details_by_rule_category': self.get_details_by_rule_category(
                payslips.mapped('details_by_salary_rule_category_ids').filtered(
                    lambda r: r.appears_on_payslip)),
            'get_lines_by_contribution_register':
                self.get_lines_by_contribution_register(
                payslips.mapped('line_ids').filtered(
                    lambda r: r.appears_on_payslip)),
        }
