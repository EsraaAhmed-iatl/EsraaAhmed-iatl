# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name': "Afi General Customizations",
    'summary': """
        General Customizations """,
    'description': """
    """,
    'author': "IATL-Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Sales',
    'version': '0.1',
    'depends': ['base', 'web', 'sale', 'sale_order_lot_selection',
                'account', 'ii_universal_discount_15','stock',
                'hr_holidays'
                ],
    'data': [
        # security
        'security/ir.model.access.csv',
        # Data
        'data/sequence.xml',
        # Views
        'views/partner_view.xml',
        'views/general_view.xml',
        'views/product_view.xml',
        'views/sale_orders_view.xml',
        'views/account_group.xml',
        'views/stock_view.xml',
        # reports
        'reports/external_layout.xml',
        'reports/reports_registration.xml',
        # 'reports/report_invoice.xml',
        # 'reports/report_sale_order.xml',
        'reports/report_sale_order_recommend.xml',
        # wizards
        'wizard/detail_movements_view.xml',
        'wizard/product_movements_view.xml',
        'wizard/wiz_sales_per_warehouse_per_customer_view.xml',
        'wizard/wiz_sales_per_warehouse_summary_view.xml',
    ],
    
    'application': True,
    'installable': True,
    'application': True,
}
