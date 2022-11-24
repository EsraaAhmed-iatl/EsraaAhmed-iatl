# -*- coding: utf-8 -*-
###########

from odoo import api, fields, models, _
import xlsxwriter
import base64
import datetime
from io import StringIO, BytesIO
from datetime import *
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from dateutil import relativedelta


class WizardPayslipCustom(models.Model):
    _name = 'paysheet.custom'
    _description = 'Print customize Payslip'

    # payslip_report = fields.Binary(string='s')
    # payslip_report_name = fields.Char(string='Payslip Name', default='Pay sheet Report.xls')
    from_date = fields.Date(string='Date From', required=True)
    # default=time.strftime('%Y-%m-01'))
    to_date = fields.Date(string='Date To', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    name = fields.Char(string="Customize Payslip")

    def print_report(self):
        for report in self:
            from_date = report.from_date
            to_date = report.to_date
            if self.from_date > self.to_date:
                raise UserError(_("You must be enter start date less than end date !"))
            report.name = 'Pay Sheet From ' + str(from_date) + ' To ' + str(to_date)
            report_title = 'Salaries From ' + str(from_date) + ' To ' + str(to_date)
            file_name = _('Pay Sheet.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Pay Sheet')
            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#808080', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format({'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            header_format.set_align('center')
            header_format.set_text_wrap()
            excel_sheet.set_row(5, 20)
            excel_sheet.set_column('F:U', 20, )
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 5
            first_row = 7

            excel_sheet.write(row, col, 'Name', header_format)
            col += 1

            excel_sheet.write(row, col, 'Bank Account', header_format)
            col += 1

            excel_sheet.write(row, col, 'Net Salary', header_format)
            col += 1

            excel_sheet.set_column(0, 4, 25)
            excel_sheet.set_row(1, 25)
            excel_sheet.merge_range(0, 0, 1, 3, 'International Investment Co.LTD', title_format)
            excel_sheet.merge_range(2, 0, 3, 3, report_title, title_format)
            excel_sheet.merge_range(3, 0, 4, 20, '', title_format)
            payslip_month_ids = report.env['hr.payslip'].search(
                [('date_to', '<=', to_date), ('date_from', '>=', from_date), ('state', '=', 'done')])
            for payslip_period in payslip_month_ids:
                slip_id = payslip_period.id
                employee = payslip_period.employee_id.id
                employee_id = payslip_period.employee_id.name
                bank_acc = payslip_period.employee_id.bank_acc
                job_id = payslip_period.employee_id.job_id.name
                employee_code = payslip_period.employee_id.code
                col = 0
                row += 1
                net = 0

                if employee_id:
                    excel_sheet.write(row, col, employee_id, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if bank_acc:
                    excel_sheet.write(row, col, bank_acc, format)


                slip_ids = payslip_period.env['hr.payslip.line'].search([('slip_id', '=', slip_id),
                                                                         ('employee_id', '=', employee)])

                net = 0.0
                for slip_line in slip_ids:
                    category = slip_line.code

                    if category == 'NET':
                        net = slip_line.amount


                col += 1
                if net:
                    excel_sheet.write(row, col, net, format)
                else:
                    excel_sheet.write(row, col, '', format)

        col = 0
        row += 1

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        wizardmodel = self.env['payslip.report.excel']
        res_id = wizardmodel.create({'name': file_name, 'file_download': file_download})
        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payslip.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
        }

    ############################################
class payslip_report_excel_custom(models.TransientModel):
    _name = 'payslip.custom.report.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
