from odoo import models


class ReportTaxNew(models.AbstractModel):
    _name = "report.ft_backend.report_tax_new"
    _inherit = "report.base_accounting_kit.report_tax"
    _description = "Tax Report (New)"
