# -*- coding: utf-8 -*-
{
    'name': "Journal Voucher Report Print",
    'summary': """
        This module allows the user to generate and print a custom Journal Voucher (JV) report print. The journal entries report is a list of all the journal vouchers of an organization and general ledger shown in chronological order. With this module, you can generate a .pdf document and take printouts of any number of journal vouchers.""",
    'description': """
        Create Journal Voucher (JV) printouts for a single or multiple entries
    """,
    "author": "One Stop Odoo",
    "website": "https://onestopodoo.com",
    "maintainer": "One Stop Odoo",
    'category': 'Report',
    "license": "LGPL-3",
    'version': '1.5',
    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/custom_header_footer.xml',
        'report/report.xml',
        'report/journal_voucher.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    "images": [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True
}
