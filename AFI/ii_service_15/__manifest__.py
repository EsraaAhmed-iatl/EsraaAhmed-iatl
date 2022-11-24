#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2017 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'AFI After Sales 15',
    'author': 'IATL IntelliSoft',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the after Sales module Odoo 15.",
    'depends': ['base', 'sale_stock','stock','sale'],
    'category': 'Sales',
    'data': [
        'data/job_order_sequence.xml',
        'security/ir.model.access.csv',
        'views/general_view.xml',
        'views/job_orders_view.xml',
        'views/partner_view.xml',
        # reports
        'reports/reports_registration.xml',
        'reports/report_job_order.xml',
        'reports/report_spare_part_form.xml',
        'reports/workshop_performance_report.xml',
        'wizard/workshop_performance.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
