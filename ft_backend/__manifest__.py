{
    "name": "Fama Backend",
    "version": "19.0.1.0.0",
    "depends": ["base", "account", "purchase", "hr", "base_accounting_kit"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        'data/email_template.xml',
        'data/ir_cron.xml',
        "views/report_action.xml",
        "views/tax_report_action.xml",
        "views/customer_invoices_payments_report_view.xml",
        "views/vendor_invoices_payments_report_view.xml",
        "views/purchase_view.xml",
        "views/account_move_view.xml",
        "views/company_view.xml",
        "views/res_partner_view.xml",
        'views/hr_employee_view.xml',
        "reports/invoice_report.xml",
        "reports/invoice_report_no_header_footer.xml",
        "reports/tax_report.xml",
        "reports/tax_report_green.xml",
        "reports/customer_invoices_payments_report.xml",
        "reports/vendor_invoices_payments_report.xml",
        "reports/purchase_order_report.xml",
        "reports/purchase_order_rfq_report.xml"
    ],
    "installable": True
}
