# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools, _
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
import datetime
from io import StringIO, BytesIO
from datetime import *
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import os
# from odoo.exceptions import UserError
from odoo.exceptions import Warning as UserError

from dateutil import relativedelta
from io import BytesIO


class WizardDetailMovements(models.Model):
    _name = 'wizard.detail.movements'
    _description = 'Print all stock movements for specific location '

    location_id = fields.Many2one('stock.location', 'Location')
    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')

    def print_report(self):
        for report in self:
            logo = report.env.user.company_id.company_header
            from_date = report.from_date
            to_date = report.to_date
            location_name = report.location_id.name
            company_id = report.env['res.company'].search([('id', '=', self.env.user.company_id.id)])
            address1 = company_id.street
            address2 = company_id.street2
            country = company_id.country_id.name
            phone = company_id.phone
            website = company_id.website
            if report.from_date > report.to_date:
                raise UserError(_("You must be enter start date less than end date !"))
            report_title = location_name + ' Movements From ' + from_date + ' to ' + to_date
            file_name = _(location_name + ' Moves.xlsx')
            fp = StringIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Product Moves')
            image_data = BytesIO(base64.b64decode(logo))  # to convert it to base64 file
            excel_sheet.insert_image('B1', 'logo.png', {'image_data': image_data})

            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#3f983f', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format({'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            header_format.set_align('center')
            header_format.set_align('vertical center')
            header_format.set_text_wrap()
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1, 'font_size': '10'})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            format.set_text_wrap()
            format_details = workbook.add_format()
            sequence_format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            sequence_format.set_align('center')
            sequence_format.set_text_wrap()
            total_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': '#808080', 'border': 1, 'font_size': '10'})
            total_format.set_align('center')
            total_format.set_text_wrap()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 7
            first_row = 9
            # excel_sheet.write_merge(0, 5, 1, 5, report_title, style_header_thin_all_main1)
            excel_sheet.merge_range(0, 1, 5, 5, report_title, title_format)
            excel_sheet.set_column(col, col, 5)
            excel_sheet.write(row, col, '#', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Date', header_format)
            col += 1
            excel_sheet.set_column(col, col, 30)
            excel_sheet.write(row, col, 'Source Location', header_format)
            col += 1
            excel_sheet.set_column(col, col, 30)
            excel_sheet.write(row, col, 'Destination Location', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Product', header_format)
            col += 1
            excel_sheet.set_column(col, col, 10)
            excel_sheet.write(row, col, 'Qty In', header_format)
            col += 1
            excel_sheet.set_column(col, col, 10)
            excel_sheet.write(row, col, 'Qty Out', header_format)
            move_ids = self.env['stock.move'].search(
                [ ('date', '<=', to_date), ('date', '>=', from_date),
                 ('state', '=', 'done'),'|',('location_id','=',report.location_id.id),('location_dest_id', '=', report.location_id.id)], order='date desc')
            if move_ids:
                for move in move_ids:
                    quantity = move.product_qty
                    date = move.date
                    Source = move.location_id.complete_name
                    location_dest = move.location_dest_id.complete_name
                    if move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage in (
                            'internal', 'transit'):
                        move_type = 'incoming'
                    elif move.location_id.usage in ('internal', 'transit') and move.location_dest_id.usage not in (
                            'internal', 'transit'):
                        move_type = 'outgoing'
                    else:
                        continue
                    col = 0
                    row += 1
                    sequence_id += 1
                    excel_sheet.write(row, col, sequence_id, sequence_format)
                    col += 1
                    if date:
                        excel_sheet.write(row, col, date, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    # write the source and destination
                    if move_type == 'incoming':
                        col += 1
                        if Source:
                            excel_sheet.write(row, col, Source, format)
                        else:
                            excel_sheet.write(row, col, '', format)
                        col += 1
                        excel_sheet.write(row, col, location_dest, format)
                    if move_type == 'outgoing':
                        col += 1
                        excel_sheet.write(row, col, Source, format)
                        col += 1
                        if location_dest:
                            excel_sheet.write(row, col, location_dest, format)
                        else:
                            excel_sheet.write(row, col, '', format)
                    col += 1
                    excel_sheet.write(row, col, move.product_id.name, format)
                    # write quants
                    if move_type == 'incoming':
                        col += 1
                        if quantity:
                            excel_sheet.write(row, col, quantity, format)
                            col += 1
                            excel_sheet.write(row, col, '', format)
                        else:
                            excel_sheet.write(row, col, '', format)
                            col += 1
                            excel_sheet.write(row, col, '', format)
                    if move_type == 'outgoing':
                        col += 1
                        if quantity:
                            excel_sheet.write(row, col, '', format)
                            col += 1
                            excel_sheet.write(row, col, quantity, format)


            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['product.movements.report.excel']
            res_id = wizardmodel.create({'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.movements.report.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class detail_movements_report_excel(models.TransientModel):
    _name = 'detail.movements.report.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
