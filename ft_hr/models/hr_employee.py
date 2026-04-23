from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_code = fields.Char(
        string="Employee Code",
        copy=False,
        readonly=True,
        default="New",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("employee_code") or vals.get("employee_code") == "New":
                vals["employee_code"] = self.env["ir.sequence"].next_by_code(
                    "ft_hr.employee.code"
                ) or "New"
        return super().create(vals_list)
