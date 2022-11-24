# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
import time
# import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.osv import osv


class HrContractLeave(models.Model):
    _inherit = 'hr.contract'

    transport_allowance = fields.Float(string='Transport + Fuel Allowance')
    taxable = fields.Boolean(string='Deduct Tax', default=True)
    eligible_si = fields.Boolean(string='Eligible For Social Insurance', default=True)
    legal_leave = fields.Selection(
        [('20', '20 day'), ('25', '25 day'),
         ('30', '30 day')], string='Legal Leave')
    grade = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'),
         ('10', '10')
         ], string='Grade')
    grade_class = fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E'), ('f', 'F')],
                                   string='Class')

    @api.onchange('legal_leave')
    def employee_legal_leave(self):
        for x in self:
            employee = x.employee_id
            if x.employee_id:
                legal_leave = x.legal_leave
                employee_id = x.employee_id.id
                update_leave = False
                if legal_leave == '20':
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave=%s"
                                                 "  WHERE id= %s", (20, employee_id))
                elif legal_leave == '25':
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave =%s"
                                                 "  WHERE id= %s", (25, employee_id))
                else:
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave=%s"
                                                 "WHERE id= %s", (30, employee_id))

class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.constrains('date_to', 'date_from')
    def _check_date(self):
        for holiday in self:
            employement_period = 0.0
            date_from = str(holiday.date_from)
            if holiday.holiday_status_id.id == 1:
                date_from = holiday.date_from
                d = date_from
                date_from = str(d.date())
                if holiday.date_from:
                    employee_id = holiday.employee_id.id
                    hr_employee = holiday.env['hr.employee'].search([('id', '=', employee_id)])
                    if not hr_employee.hiring_date:
                        raise UserError(_('Please Add employee Hiring date!'))
                    hiring = str(hr_employee.hiring_date)
                    holiday_to = datetime.strptime(date_from, '%Y-%m-%d')
                    hiring_date = datetime.strptime(hiring, '%Y-%m-%d')
                    employement_period = (holiday_to - hiring_date).days
                    if employement_period < 365.25:
                        raise UserError(_('You can not request leave before you complete Year!'))
