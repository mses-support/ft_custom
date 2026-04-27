from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_code = fields.Char(
        string="Employee Code",
        copy=False,
    )

    @api.model
    def _cleanup_legacy_employee_code_values(self):
        legacy_employees = self.with_context(active_test=False).search(
            [("employee_code", "=", "New")]
        )
        if legacy_employees:
            legacy_employees.write({"employee_code": False})
        return True
