from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    basic_salary = fields.Float(
        string='Basic Salary',
        compute='_compute_salary_rule_totals',
        store=True,
        digits='Payroll',
    )
    temporary_input = fields.Float(
        string='Temporary Input',
        compute='_compute_salary_rule_totals',
        store=True,
        digits='Payroll',
    )
    employee_bonus = fields.Float(
        string='Employee Bonus',
        compute='_compute_salary_rule_totals',
        store=True,
        digits='Payroll',
    )
    gross_salary = fields.Float(
        string='Gross Salary',
        compute='_compute_salary_rule_totals',
        store=True,
        digits='Payroll',
    )
    net_salary = fields.Float(
        string='Net Salary',
        compute='_compute_salary_rule_totals',
        store=True,
        digits='Payroll',
    )

    @api.depends('line_ids.total', 'line_ids.code', 'line_ids.salary_rule_id.code')
    def _compute_salary_rule_totals(self):
        """Aggregate payslip line totals by rule code for list-view visibility."""
        target_map = {
            'BASIC': 'basic_salary',
            'TMPIN': 'temporary_input',
            'BONUS': 'employee_bonus',
            'GROSS': 'gross_salary',
            'NET': 'net_salary',
        }

        for slip in self:
            totals = {field_name: 0.0 for field_name in target_map.values()}
            for line in slip.line_ids:
                code = (line.salary_rule_id.code or line.code or '').upper()
                field_name = target_map.get(code)
                if field_name:
                    totals[field_name] += line.total

            slip.basic_salary = totals['basic_salary']
            slip.temporary_input = totals['temporary_input']
            slip.employee_bonus = totals['employee_bonus']
            slip.gross_salary = totals['gross_salary']
            slip.net_salary = totals['net_salary']
