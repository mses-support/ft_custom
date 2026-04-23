from odoo import models
from odoo.addons.base_accounting_kit.wizard.xlsx_mixin import ReportXlsxMixin


class KitAccountTaxReport(models.TransientModel, ReportXlsxMixin):
    _inherit = "kit.account.tax.report"

    def _print_report(self, data):
        if not self.env.context.get("use_new_tax_report"):
            return super()._print_report(data)

        data["form"].update({"tax_scope": self.tax_scope})
        return self.env.ref("ft_backend.action_report_account_tax_new").report_action(
            self, data=data
        )
