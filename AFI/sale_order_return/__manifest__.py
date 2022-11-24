# -*- coding: utf-8 -*-
{
    'name': "Sale Order Return",

    'summary': """
        """,

    'description': """
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'license': "AGPL-3",
    'category': "Hidden",
    'version': "0.1",
    'depends': ['sale_stock', 'sale_management', 'order_return'],
    'data': [
        # 'security/ir.model.access.csv',
        'wizard/order_return_picking_views.xml',
        'data/return_sequense.xml',
        'views/order_return_views.xml',
        'views/sale_views.xml',
        'views/product_category_view.xml',
    ],
}
