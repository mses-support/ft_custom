from odoo import api, SUPERUSER_ID


def _ref(env, xmlid):
    return env.ref(xmlid, raise_if_not_found=False)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    act_bs = _ref(env, "ft_backend.action_ft_balance_sheet_dynamic")
    act_is = _ref(env, "ft_backend.action_ft_income_statement_dynamic")
    if not (act_bs and act_is):
        return

    # Force well-known generic statement menus to dynamic actions
    menu_map = {
        "base_accounting_kit._account_financial_reports_balance_sheet": act_bs,
        "base_accounting_kit.account_financial_reports_profit_loss": act_is,
        "ft_backend.menu_ft_balance_sheet_report": act_bs,
        "ft_backend.menu_ft_income_statement_report": act_is,
    }
    for xmlid, action in menu_map.items():
        menu = _ref(env, xmlid)
        if menu:
            menu.action = f"ir.actions.client,{action.id}"

    # Also repoint old wizard actions by changing menu actions that still target financial.report wizard
    menus = env["ir.ui.menu"].search([("action", "like", "ir.actions.act_window,%")])
    for menu in menus:
        if not menu.action:
            continue
        parts = menu.action.split(",")
        if len(parts) != 2:
            continue
        try:
            action_id = int(parts[1])
        except ValueError:
            continue
        act = env["ir.actions.act_window"].browse(action_id)
        if not act.exists():
            continue
        if act.res_model != "financial.report":
            continue
        name = (menu.name or "").lower()
        if "balance" in name:
            menu.action = f"ir.actions.client,{act_bs.id}"
        elif "profit" in name or "income" in name or "loss" in name:
            menu.action = f"ir.actions.client,{act_is.id}"
