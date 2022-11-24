{
    'name': 'Hr AFI Customization Module',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'category': 'Human Resources',
    'description': """Afi hr customization """,

    'depends': ['hr', 'hr_payroll', 'hr_payroll_account',
                'hr_attendance', 'account', 'hr_holidays',
                'is_accounting_approval_15',
                ],
    'data': [
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        # date
        'data/hr_loan_sequence.xml',
        # Views
        'wizard/delay_loan_view.xml',
        'views/end_service_view.xml',
        'views/is_hr_loan_view.xml',
        'views/is_hr_view.xml',
        'views/is_hr_overtime_view.xml',
        'views/is_hr_trip.xml',
        'views/is_hr_payslip_view.xml',
        'wizard/lta_transport_batch_view.xml',
        'views/is_lta_transport_view.xml',
        'views/is_employee_view.xml',
        'views/buy_leave_view.xml',
        # reports
        'report/hr_report.xml',
        'report/hr_trip_report.xml',
        # wizard
        'wizard/pay_sheet_view.xml',
        'wizard/wizard_overtime_view.xml',
        'wizard/wizard_lta_transport_view.xml',
        'wizard/pay_sheet_view_custom.xml',

    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
