#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2017 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'Afi Costing Module 15',
    'author': 'IATL IntelliSoft',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the accounting module. Odoo 15.",
    'depends': ['base', 'sale', 'stock_account'],
    'category': 'Accounting',
    'data': [
        # 'security/security_view.xml',
        # 'security/ir.model.access.csv',
        # 'data/load.xml',
        'views/general_view.xml',
        'views/product_view.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
