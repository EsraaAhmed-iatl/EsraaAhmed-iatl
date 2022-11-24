# -*- coding: utf-8 -*-
{
    'name': "Order Return",

    'summary': """
        """,

    'description': """
        
    """,

     'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'license': "AGPL-3",
    'category': "Hidden",
    'version': '0.1',

    'depends': ['base', 'stock', 'purchase','account'],

    'data': [
        'security/security_views.xml',
        'security/ir.model.access.csv',
        'wizard/order_return_picking_views.xml',
        'views/return_reason_views.xml',
        'views/return_order_views.xml',
        'views/stock_picking_views.xml',
        'reports/order_return_report.xml',
        'reports/reports.xml',
    ],

}
