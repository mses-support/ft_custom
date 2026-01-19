{
    "name": "Fama Backend",
    "version": "19.0.1.0.0",
    "depends": ["base","account","purchase"],
    "data": [
        "security/security.xml",
        'data/email_template.xml',
        'data/ir_cron.xml',
        "views/report_action.xml",
        "views/purchase_view.xml",
        "views/company_view.xml",
        'views/hr_employee_view.xml',
        "reports/invoice_report.xml"
    ],
    "installable": True
}