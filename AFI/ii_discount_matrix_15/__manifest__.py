# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name': "Afi Discount Matrix",

    'summary': """
        Sales Discount Matrix""",

    'description': """
    """,

    'author': "IATL-Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # List of modules which are demanded to be installed first
    'depends': ['hr', 'ii_universal_discount_15'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/discount_matrix_view.xml',
    ],
    
    'application': True,
    'installable': True,
    'application': True,
}
