# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Ammu Raj(odoo@cybrosys.com)
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
from odoo import api, fields, models


class HrPayslip(models.Model):
    """ This class is used to create the bonus reasons. """
    _inherit = "hr.payslip"

    def _apply_bonus_input(self):
        """Insert/update BONUS input line for the selected period."""
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to or not slip.struct_id:
                continue
            bonus_rule = self.env.ref('employee_bonus_manager.hr_salary_rule_bonus')
            if bonus_rule not in slip.struct_id.rule_ids:
                continue
            bonus_requests = self.env['bonus.request'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'accounting'),
                ('move_id.state', '=', 'posted'),
                ('move_id.date', '>=', slip.date_from),
                ('move_id.date', '<=', slip.date_to),
            ])
            amount = sum(bonus_requests.mapped('bonus_amount'))
            bonus_line = slip.input_line_ids.filtered(lambda line: line.code == 'BONUS')[:1]
            if bonus_line:
                bonus_line.amount = amount
            else:
                slip.input_line_ids = [(0, 0, {
                    'name': 'Bonus',
                    'code': 'BONUS',
                    'contract_id': slip.contract_id.id,
                    'amount': amount,
                })]

    @api.onchange('employee_id', 'date_from', 'date_to', 'struct_id')
    def _onchange_bonus_input(self):
        """Keep bonus input synced even if other modules override onchange methods."""
        self._apply_bonus_input()

    def action_compute_sheet(self):
        """Ensure BONUS input is present before computing payslip lines."""
        self._apply_bonus_input()
        return super().action_compute_sheet()
