
{
    'name': 'FT ZATCA Custom',
    'version': '1.0.2',
    'summary': 'ZATCA SAR conversion using invoice report templates',
    'category': 'Accounting',
    'author': 'Ajay / Fama Tech',
    'depends': ['account', 'ft_backend'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'report/invoice_zatca_templates.xml',
    ],
    'installable': True,
    'application': False,
}
