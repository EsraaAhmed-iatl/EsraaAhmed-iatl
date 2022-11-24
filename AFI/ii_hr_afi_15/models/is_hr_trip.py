# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_compare
import math


class HrTrip(models.Model):
    _name = 'hr.trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char(string='Description')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, default=_default_employee)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    emp_salary = fields.Monetary(string="Employee Salary", related="employee_id.contract_id.wage")
    trip_start_date = fields.Datetime(string="Trip Date From")
    trip_end_date = fields.Datetime(string="Trip Date To")
    # maintenance = fields.Char(string='Maintenance')
    trip_dist = fields.Char(string='Trip Destination')
    no_of_days = fields.Float(string='No Of Days')
    added_no_of_days = fields.Float(string='Added No Of Days', default=2)
    employee_account = fields.Many2one('account.account', string="Debit Account")
    trip_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                related='department_id.analytic_debit_account_id',readonly=True,
                                                string="Analytic Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    note = fields.Text(string='Notes')
    trip_no = fields.Char(string='No')
    day_in_words = fields.Char(string='Day', compute='get_day_in_words')
    day_start_in_words = fields.Char(string='Day Start', compute='get_day_in_words')
    trip_amount = fields.Float(string='Amount', compute='get_amount')
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('approve', 'Approved'), ('confirm', 'Confirmed'),
         ('approve2', 'Department Days Approved'), ('confirm2', 'Hr Days Confirm'),('done', 'Done'),
         ('refuse', 'Refused')],
        'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help='The status is set to \'To Submit\', when a trip request is created.\
                      \nThe status is \'Approved\', when trip request is confirmed by department manager.\
                      \nThe status is \'Confirmed\', when trip request is confirmed by hr manager.\
                      \nThe status is \'Department Days Approved\', when trip DAys is approved by department manager.\
                      \nThe status is \'Hr Days Confirm\', when trip days approved by hr manager.\
                      \nThe status is \'Refused\', when trip request is refused.')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)

        if employee_id:
            time_delta = to_dt - from_dt
            return math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

    @api.onchange('trip_start_date', 'trip_start_date')
    def _onchange_date_from(self):
        date_from = self.trip_start_date
        date_to = self.trip_end_date
        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.no_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.no_of_days = 0

    @api.onchange('trip_end_date')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        date_from = self.trip_start_date
        date_to = self.trip_end_date

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.no_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.no_of_days = 0

    @api.depends('no_of_days')
    def get_amount(self):
        for trip in self:
            trip.trip_amount = 0.0
            if trip.no_of_days and trip.employee_id.contract_id:
                employee_salary = trip.employee_id.contract_id.wage
                added_no_of_days = trip.added_no_of_days
                no_of_days = trip.no_of_days * added_no_of_days
                trip.trip_amount = (employee_salary / 30) * no_of_days

    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda HrTrip: HrTrip.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a Trip which is not draft or refused!'))
            return super(HrTrip, rec).unlink()

    def trip_first_approve(self):
        for rec in self:
            rec.state = 'approve'

    def trip_second_approve(self):
        for rec in self:
            rec.state = 'approve2'

    def trip_first_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def trip_second_confirm(self):
        for rec in self:
            rec.state = 'confirm2'

    def trip_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    def trip_reset(self):
        for rec in self:
            rec.state = 'draft'

    def trip_account_done(self):
        amount = 0.0
        for trip in self:
            precision = trip.env['decimal.precision'].precision_get('trip')
            employee_account = trip.employee_account.id
            trip_account = trip.trip_account.id
            journal_id = trip.journal_id.id
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            trip_hour = 0.0
            per_diem = 0.0
            trip_date = trip.trip_end_date
            trip_name = trip.employee_id.name+' trip'
            employee_salary = trip.emp_salary
            grade = trip.employee_id.contract_id.grade
            if grade == '1':
                per_diem = 500

            if grade == '2':
                per_diem = 400
            if grade in ('3', '4'):
                per_diem = 300
            if grade in ('5', '6', '7'):
                per_diem = 200
            if grade in ('8', '9', '10'):
                per_diem = 400
            if not grade:
                raise UserError(_('Please Enter employee grade!'))
            amount = trip.trip_amount
            move_dict = {
                'narration': trip_name,
                'ref': '/',
                'journal_id': journal_id,
                'date': trip_date,
            }
            debit_line = (0, 0, {
                        'name': trip_name,
                        'partner_id': False,
                        'account_id': employee_account,
                        'journal_id': journal_id,
                        'date': trip_date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_account_id': trip.analytic_debit_account_id.id,
                        'tax_line_id': 0.0,
                    })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                        'name': trip_name,
                        'partner_id': False,
                        'account_id': trip_account,
                        'journal_id': journal_id,
                        'date': trip_date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_account_id': False,
                        'tax_line_id': 0.0,
                    })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            trip.write({'move_id': move.id})
            move.post()
        trip.state = 'done'

    @api.depends('trip_start_date', 'trip_end_date')
    def get_day_in_words(self):
        for rec in self:
            rec.day_start_in_words = ''
            rec.day_in_words = ''
            if rec.trip_start_date:
                trip_start_date = rec.trip_start_date
                day_start_name = datetime.datetime.strptime(str(trip_start_date.date()), '%Y-%m-%d')
                rec.day_in_words = datetime.datetime.strftime(day_start_name, "%A")
            if rec.trip_end_date:
                trip_end_date = rec.trip_end_date
                day_end_name = datetime.datetime.strptime(str(trip_end_date.date()), '%Y-%m-%d')
                rec.day_start_in_words = datetime.datetime.strftime(day_end_name, "%A")
