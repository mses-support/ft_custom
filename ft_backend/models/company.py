from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    po_daily_limit = fields.Float(string="PO Daily Approval Limit")
    po_monthly_limit = fields.Float(string="PO Monthly Approval Limit")


