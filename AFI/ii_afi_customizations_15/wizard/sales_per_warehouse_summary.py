# -*- coding: utf-8 -*-
###########

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
from io import BytesIO
from PIL import Image as Image


def _offset_format_timestamp(src_tstamp_str, src_format, dst_format, ignore_unparsable_time=True, context=None):
    """
    Convert a source timestamp string into a destination timestamp string, attempting to apply the
    correct offset if both the server and local timezone are recognized, or no
    offset at all if they aren't or if tz_offset is false (i.e. assuming they are both in the same TZ).

    @param src_tstamp_str: the str value containing the timestamp.
    @param src_format: the format to use when parsing the local timestamp.
    @param dst_format: the format to use when formatting the resulting timestamp.
    @param server_to_client: specify timezone offset direction (server=src and client=dest if True, or client=src and server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str cannot be parsed
                                   using src_format or formatted using dst_format.

    @return: destination formatted timestamp, expressed in the destination timezone if possible
            and if tz_offset is true, or src_tstamp_str if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False
    res = src_tstamp_str
    if src_format and dst_format:
        try:
            # dt_value needs to be a datetime.datetime object (so no time.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.strptime(src_tstamp_str, src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone(context['tz'])
                    dst_tz = pytz.timezone('UTC')
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception as e:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception as e:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class sales_per_warehouse_summary(models.TransientModel):
    _name = 'sales.warehouse.summary'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)


    def sales_per_warehouse_summary_excel(self):
        file_name = _('Sales Per Warehouse Summary.xlsx')
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Sales Per Warehouse Summary')
        path = os.path.join(os.path.dirname(__file__) + "/logo.jpeg")
        image_file = Image.open(path)
        img = image_file.resize((90, 53))
        image_data = BytesIO()
        img.save(image_data, format='PNG')
        worksheet.insert_image('E1', path, {'image_data': image_data})
        worksheet.set_column(2, 2, 38)
        worksheet.set_column(3, 4, 14)
        format = workbook.add_format({'bold': True})
        format.set_num_format('#,##0.00')
        format_details = workbook.add_format()
        format_details.set_num_format('#,##0.00')
        worksheet.write('B1', 'Sales Per Warehouse Summary', format)
        worksheet.write('B3', date.today().year)
        data = self.read()[0]

        if self.from_date > self.to_date:
            raise ValidationError(_("You must be enter start date less than end date !"))
        my_date = 'FROM DATE: ' + self.from_date + ' TO DATE: ' + self.to_date
        worksheet.write('B4', my_date, format)
        warehouse = self.warehouse_id.name
        worksheet.write('B5', warehouse, format)
        worksheet.merge_range('B9:Z9', 'Sales Per Warehouse Per Customer', format)
        worksheet.write('B11', '#', format)
        worksheet.write('C11', 'Customer', format)
        worksheet.write('D11', 'Total', format)
        worksheet.write('E11', 'Balance', format)
        am_lst = []
        rs_lst = []

        from_date = (datetime.strptime(data.get('from_date').encode('utf-8') + ' 00:00:00',
                                       DEFAULT_SERVER_DATETIME_FORMAT)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        to_date = (datetime.strptime(data.get('to_date').encode('utf-8') + ' 00:00:00',
                                     DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=1)).strftime(
            DEFAULT_SERVER_DATETIME_FORMAT)
        from_date = _offset_format_timestamp(from_date, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT,
                                             ignore_unparsable_time=True, context=self.env.context)
        to_date = _offset_format_timestamp(to_date, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT,
                                           ignore_unparsable_time=True, context=self.env.context)
        # inital start for data
        col = 13
        # get total per warehouse per customer
        all_customers = self.env['res.partner'].search([], order='name')
        line_count = 0
        for cust in all_customers:
            self.env.cr.execute('''SELECT sum(amount_total), sum(residual) FROM account_invoice where
                                        id in (
                                                select invoice_id from sale_order_invoice_rel
                                                where order_id in (
                                                                    select id from sale_order
                                                                    where date_order between '%s' and '%s'
                                                                    and state in ('progress','done') and warehouse_id = %s
                                                                    and partner_id = %s
                                                                    )
                                                )''' % (from_date, to_date, self.warehouse_id.id, cust.id))
            # fetch results
            result = self.env.cr.fetchall()
            if result and result[0][0] is not None and result[0][1] is not None:
                line_count += 1
                worksheet.write(col, 1, line_count)
                worksheet.write(col, 2, cust.name, format_details)
                worksheet.write(col, 3, result[0][0], format_details)
                am_lst.append(result[0][0])
                worksheet.write(col, 4, result[0][1], format_details)
                rs_lst.append(result[0][1])
                col += 1
        # print totals
        worksheet.write(col, 1, "Total:", format)
        worksheet.write(col, 3, sum(am_lst), format)
        worksheet.write(col, 4, sum(rs_lst), format)
        worksheet.set_landscape()
        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


############################################
class sale_report_excel(models.TransientModel):
    _name = 'sale.report.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
