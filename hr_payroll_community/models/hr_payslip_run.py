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
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class HrPayslipRun(models.Model):
    """Create new model for getting Payslip Batches"""
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True, help="Name for Payslip Batches",
                       string="Name")
    slip_ids = fields.One2many('hr.payslip',
                               'payslip_run_id',
                               string='Payslips',
                               help="Choose Payslips for Batches")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_approval', 'HR'),
        ('management_approval', 'Management Approval'),
        ('final_approval', 'Final Approval'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
                               help="Status for Payslip Batches")
    date_start = fields.Date(string='Date From', required=True,
                             help="start date for batch",
                             default=lambda self: fields.Date.to_string(
                                 date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           help="End date for batch",
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1,
                                                               days=-1)).date())
                           )
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all"
                                      "payslips generated from here are refund"
                                      "payslips.")

    def action_payslip_run(self):
        """Function for state change"""
        return self.write({'state': 'draft'})

    def _check_approval_group(self, group_xmlid, error_message):
        """Validate current user is allowed to perform approval action."""
        if self.env.is_superuser():
            return
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(error_message)

    def action_set_hr_approval(self):
        """Move draft batches to HR approval."""
        batches = self.filtered(lambda batch: batch.state == 'draft')
        if not batches:
            return True
        self._check_approval_group(
            'hr_payroll_community.group_hr_payslip_batch_hr_approver',
            _("Only HR approvers can move the batch to HR stage."),
        )
        batches.write({'state': 'hr_approval'})
        return True

    def action_set_management_approval(self):
        """Move batches from HR stage to management stage."""
        batches = self.filtered(lambda batch: batch.state in ('draft', 'hr_approval'))
        if not batches:
            return True
        self._check_approval_group(
            'hr_payroll_community.group_hr_payslip_batch_management_approver',
            _("Only Management approvers can move the batch to Management Approval stage."),
        )
        invalid = batches.filtered(lambda batch: batch.state != 'hr_approval')
        if invalid:
            raise UserError(_("Batch must be in HR stage before Management Approval."))
        batches.write({'state': 'management_approval'})
        return True

    def action_set_final_approval(self):
        """Move batches from management stage to final stage."""
        batches = self.filtered(
            lambda batch: batch.state in ('draft', 'hr_approval', 'management_approval')
        )
        if not batches:
            return True
        self._check_approval_group(
            'hr_payroll_community.group_hr_payslip_batch_final_approver',
            _("Only Final approvers can move the batch to Final Approval stage."),
        )
        invalid = batches.filtered(lambda batch: batch.state != 'management_approval')
        if invalid:
            raise UserError(
                _("Batch must be in Management Approval stage before Final Approval.")
            )
        batches.write({'state': 'final_approval'})
        return True

    def close_payslip_run(self):
        """Function for state change"""
        self._check_approval_group(
            'hr_payroll_community.group_hr_payslip_batch_final_approver',
            _("Only Final approvers can close payslip batches."),
        )
        invalid = self.filtered(lambda batch: batch.state != 'final_approval')
        if invalid:
            raise UserError(_("Batch must be in Final Approval stage before closing."))
        return self.write({'state': 'close'})
