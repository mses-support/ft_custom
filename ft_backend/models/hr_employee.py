from odoo import models, fields, api
from datetime import timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    housing_allowance = fields.Monetary(
        string="Housing Allowance",
        currency_field='currency_id'
    )
    transportation_allowance = fields.Monetary(
        string="Transportation Allowance",
        currency_field='currency_id'
    )
    communication_allowance = fields.Monetary(
        string="Communication Allowance",
        currency_field='currency_id'
    )
    mileage_allowance = fields.Monetary(
        string="Mileage Allowance",
        currency_field='currency_id'
    )
    other_allowance = fields.Monetary(
        string="Other Allowance",
        currency_field='currency_id'
    )

    net_salary = fields.Monetary(
        string="Net Salary",
        compute="_compute_net_salary",
        store=True,
        currency_field='currency_id',
        readonly=True
    )

    iqama_number = fields.Char(
        string="Iqama Number"
    )

    iqama_expiry_date = fields.Date(
        string="Iqama Expiry Date"
    )

    iqama_reminder_days = fields.Integer(
        string="Reminder Before Expiry (Days)",
        default=30,
        help="Number of days before Iqama expiry to send email notification."
    )

    iqama_expiry_notified = fields.Boolean(
        string="Iqama Expiry Notified",
        default=False,
        copy=False
    )




    @api.depends(
        'wage',
        'housing_allowance',
        'transportation_allowance',
        'communication_allowance',
        'mileage_allowance',
        'other_allowance'
    )
    def _compute_net_salary(self):
        for employee in self:
            employee.net_salary = (
                (employee.wage or 0.0)
                + (employee.housing_allowance or 0.0)
                + (employee.transportation_allowance or 0.0)
                + (employee.communication_allowance or 0.0)
                + (employee.mileage_allowance or 0.0)
                + (employee.other_allowance or 0.0)
            )


    # -------------------------
    # Reset notification if expiry date changes
    # -------------------------
    @api.onchange('iqama_expiry_date')
    def _onchange_iqama_expiry_date(self):
        self.iqama_expiry_notified = False


    @api.model
    def _cron_iqama_expiry_reminder(self):
        today = fields.Date.today()

        employees = self.search([
            ('iqama_expiry_date', '!=', False),
            ('iqama_expiry_notified', '=', False),
            ('work_email', '!=', False),
        ])

        for emp in employees:
            reminder_date = emp.iqama_expiry_date - timedelta(days=emp.iqama_reminder_days)

            if reminder_date <= today:
                template = self.env.ref(
                    'employee_allowance_iqama.email_template_iqama_expiry',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(emp.id, force_send=True)

                emp.iqama_expiry_notified = True

