# -*- coding: utf-8 -*-
{
    'name': "Afi SO Config Approve_15",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','sale','ii_discount_matrix_15', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/so_view.xml',
        'views/views.xml',
        'views/so_configuration_approve_view.xml',
        'views/account_payment_term_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
