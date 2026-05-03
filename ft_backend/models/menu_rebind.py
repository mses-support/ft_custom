from odoo import models


class FtMenuRebind(models.AbstractModel):
    _name = "ft.menu.rebind"
    _description = "Force dynamic financial menu bindings"

    def _register_hook(self):
        res = super()._register_hook()
        env = self.env
        # Replace stale Community-incompatible client actions.
        stale_actions = env["ir.actions.client"].sudo().search([("tag", "=", "account_report")])
        for action in stale_actions:
            name = (action.name or "").lower()
            if "balance" in name or "income" in name or "profit" in name or "loss" in name:
                action.write({"tag": "ft_financial_report"})
                ctx = {}
                if isinstance(action.context, dict):
                    ctx = dict(action.context)
                if "balance" in name:
                    ctx["report_type"] = "balance_sheet"
                else:
                    ctx["report_type"] = "income_statement"
                action.context = str(ctx)

        act_bs = env.ref("ft_backend.action_ft_balance_sheet_dynamic", raise_if_not_found=False)
        act_is = env.ref("ft_backend.action_ft_income_statement_dynamic", raise_if_not_found=False)
        if not (act_bs and act_is):
            return res

        mapping = {
            "base_accounting_kit._account_financial_reports_balance_sheet": act_bs,
            "base_accounting_kit.account_financial_reports_profit_loss": act_is,
            "ft_backend.menu_ft_balance_sheet_report": act_bs,
            "ft_backend.menu_ft_income_statement_report": act_is,
        }
        for xmlid, action in mapping.items():
            menu = env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.sudo().write({"action": f"ir.actions.client,{action.id}"})

        menus = env["ir.ui.menu"].sudo().search([("action", "!=", False)])
        for menu in menus:
            action = menu.action
            if not action:
                continue
            # Odoo 19 keeps this as an action record; older versions could expose a string.
            if isinstance(action, str):
                parts = action.split(",")
                if len(parts) != 2 or parts[0] != "ir.actions.act_window":
                    continue
                try:
                    act_id = int(parts[1])
                except ValueError:
                    continue
                action = env["ir.actions.act_window"].sudo().browse(act_id)
            if not action.exists() or action.type != "ir.actions.act_window":
                continue
            if getattr(action, "res_model", None) != "financial.report":
                continue
            label = (menu.name or "").lower()
            if "balance" in label:
                menu.write({"action": f"ir.actions.client,{act_bs.id}"})
            elif "profit" in label or "income" in label or "loss" in label:
                menu.write({"action": f"ir.actions.client,{act_is.id}"})

        return res
