# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, Warning
import babel
import time
from dateutil.relativedelta import relativedelta
from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class DelayLoan(models.TransientModel):
    _name = 'delay.loan'
    _description = 'Delay loan for all selected employees'

    loan_id = fields.Many2one('hr.loan', string='Loan')
    loan_line_id = fields.Many2one('hr.loan.line', 'Line', domain="[('loan_id', '=', loan_id)]")

    def compute_delay_loan(self):
        for rec in self:
            loan_line = rec.env['hr.loan.line']
            loan_id = rec.loan_id
            loan_line_id = rec.loan_line_id
            if loan_line_id:
                loan_line_id.write({'stop': True, 'notes': 'Stopped'})
                # loan_line_id.stop = True
                new_loan_id = loan_id.loan_line_ids[-1].paid_date + relativedelta(months=1)
                loan_line_val = {
                    'paid_date': new_loan_id,
                    'employee_id': loan_id.employee_id.id,
                    'paid_amount': loan_line_id.paid_amount,
                    'loan_id': loan_id.id,
                }
                loan_line.create(loan_line_val)




    # def compute_delay_loan(self):
    #     for rec in self:
    #         loan_line = rec.env['hr.loan.line']
    #         loan_id = rec.loan_id
    #         paid_amount = 0
    #         if loan_id:
    #             loan_line_rec = loan_id.loan_line_ids.search(
    #                 [('paid_date', '>=', rec.date_from), ('paid_date', '<=', rec.date_to)
    #                     , ('loan_id.state', '=', 'account_approve'), ('employee_id', '=', loan_id.employee_id.id)])
    #             if not loan_line_rec:
    #                 raise UserError(_('التاريخ الذي قمت بادخاله غير موجود في  هذه السلفية'))
    #             else:
    #                 employee_id = loan_id.employee_id
    #                 loan_line_ids = loan_line.search(
    #                     [('employee_id', '=', employee_id.id), ('paid_date', '<=', rec.date_to)
    #                         , ('paid_date', '>=', rec.date_from), ('paid', '=', False), ('loan_id.state', '=', 'account_approve')])
    #             for loan_line_id in loan_line_ids:
    #                 paid_amount += loan_line_id.paid_amount
    #                 installment_amount = loan_line_id.loan_id.installment_amount
    #                 paid_date = loan_line_id.paid_date
    #                 loan_update_id = loan_line_id.id
    #                 if paid_amount == installment_amount:
    #                     self._cr.execute(
    #                         "update hr_loan_line set stopped=%s   where loan_id=%s and paid_date =%s and id = %s",
    #                         (True, loan_id.id, paid_date, loan_update_id))
    #                 else:
    #                     self._cr.execute(
    #                         "update hr_loan_line set stopped=%s   where paid_date =%s ",
    #                         (True, paid_date,))
    #             per_loan = loan_line.search([('employee_id', '=', employee_id.id), ('loan_id.state', '=', 'account_approve')
    #                                          ], order="paid_date asc")
    #             for per in per_loan[-1]:
    #                 per_date_pay = per.paid_date
    #                 per_paid_amount = per.paid_amount
    #                 per_date_pay = datetime.strptime(per_date_pay, '%Y-%m-%d') + relativedelta(months=1)
    #                 per_loan_id = per.loan_id
    #                 pre_installment = per.loan_id.installment_amount
    #                 if pre_installment == per_paid_amount:
    #                     paid_amount = paid_amount
    #                 else:
    #                     print(paid_amount)
    #                     paid_amount = paid_amount + per_paid_amount - pre_installment
    #                     self._cr.execute(
    #                         "update hr_loan_line set paid_amount=%s   where id = %s",
    #                         (pre_installment, per.id))
    #                 new_month = paid_amount / pre_installment
    #                 counter = 0
    #                 loan_diff = paid_amount - pre_installment * int(new_month)
    #
    #                 if loan_diff > pre_installment:
    #                     new_month += 1
    #                     loan_diff = loan_diff - pre_installment
    #                 else:
    #                     loan_diff = loan_diff
    #                 for i in range(1, int(new_month + 1)):
    #                     if i != new_month + 1:
    #                         loan_line.create({
    #                             'paid_date': per_date_pay,
    #                             'paid_amount': round(pre_installment, 2),
    #                             'employee_id': per.employee_id.id,
    #                             'loan_id': per_loan_id.id})
    #                         per_date_pay = per_date_pay + relativedelta(months=1)
    #                 if loan_diff > 0:
    #                     loan_line.create({
    #                         'paid_date': per_date_pay,
    #                         'paid_amount': loan_diff,
    #                         'employee_id': per.employee_id.id,
    #                         'loan_id': per_loan_id.id})
    #                     counter += 1
