from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
import calendar


class Payslip(models.Model):
    _inherit = "hr.payslip"

    bank_acct_num = fields.Char("Bank Account Number")
    unpaid_leave = fields.Float("Unpaid Leave", readonly=True, compute='compute_unpaid', store=True)
    # deductions
    personal_loan = fields.Float("Personal Loan", readonly=True, compute='get_loan', store=True)
    short_loan = fields.Float("Monthly Loan", readonly=True, compute='get_short_loan', store=True)
    income_tax = fields.Float("Tax Amount", readonly=True, compute='get_tax_amount', store=True)
    family_burdens = fields.Float("Family burdens", readonly=True, compute='get_tax_amount', store=True)
    representation_allw = fields.Float("Representation allowance", readonly=True, compute='get_represntation_allw',
                                       store=True)
    net_salary = fields.Float("Net Salary", compute='get_net_salary', store=True)
    penalties_deduction = fields.Float("Penalty")
    mon_lost_hours = fields.Float(string="Month Lost of Hours", compute='compute_month_lost_hours', store=True,
                                  readonly=True)
    worked_days = fields.Float(string='Days', compute='_compute_days', store=True)
    no_of_days = fields.Integer(string='Days', compute='_compute_days', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                    \n* If the payslip is confirmed by hr, the status is \'Confirmed\'.
                    \n* If the payslip is under verification, the status is \'Waiting\'.
                    \n* If the payslip is confirmed by account then status is set to \'Done\'.
                    \n* When user cancel payslip the status is \'Rejected\'.""")

    @api.depends('employee_id', 'line_ids')
    def get_net_salary(self):
        for rec in self:
            rec.net_salary = 0
            net = 0.00
            total = 0.00
            if rec.line_ids and rec.employee_id:
                    payslip_line_ids = self.env['hr.payslip.line'].search([('employee_id', '=', rec.employee_id.id),
                                                                          ('code', '=', 'NET'),
                                                                          ('slip_id', '=', rec.id)])

                    for slip in payslip_line_ids:
                        total = slip.total
            rec.net_salary = total

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        days = 0
        month_range = 1
        for slip in self:
            slip.worked_days = 0
            if slip.date_from and slip.date_to:
                date_from = datetime.strptime(str(slip.date_from), '%Y-%m-%d')
                month_range = calendar.monthrange(date_from.year, date_from.month)[1]
                date_to = datetime.strptime(str(slip.date_to), '%Y-%m-%d')
                days = (date_to - date_from).days + 1
            slip.no_of_days = days
            if month_range > 0:
                worked_days = float(days)/(month_range)
            else:
                raise Warning(_("Please Enter Valid Dates for this payslip "))
            if worked_days > 1.00:
                slip.worked_days = 1
            else:
                slip.worked_days = worked_days

    def action_hr_confirm(self):
        for rec in self:
            rec.compute_sheet()
            rec.state = 'confirm'

    @api.depends('employee_id')
    def get_represntation_allw(self):
        for x in self:
            x.representation_allw = 0
            if x.employee_id:
                is_mananger = x.employee_id.is_manager
                if is_mananger:
                    x.representation_allw = 20
                else:
                    x.representation_allw = 0.0

    @api.depends('employee_id', 'no_of_days')
    def get_tax_amount(self):
        for payslip in self:
            payslip.income_tax = 0
            payslip.family_burdens = 0
            if payslip.worked_days:
                employee_salary = payslip.contract_id.wage*payslip.worked_days
                representation_allw = payslip.representation_allw
                social = employee_salary * .08
                family_member = payslip.employee_id.family_member
                family_allowance = family_member * 8.33
                # family_allowance = 49.98
                if payslip.contract_id.taxable:
                    age = payslip.employee_id.age_in_years
                    age_allowance = 0.0
                    if age >= 50:
                        age_allowance = 600
                    taxable_amount = employee_salary - social - representation_allw - family_allowance - age_allowance
                    tax = taxable_amount * .15
                    # print ('=========', taxable_amount - 40 - 75 - 1230)
                    payslip.income_tax = taxable_amount
                else:
                    payslip.income_tax = 0.0
                payslip.family_burdens = family_allowance

    @api.depends('employee_id')
    def compute_unpaid(self):
        for x in self:
            x.unpaid_leave = 0
            # if x.worked_days_line_ids:
            unpaid_sum = 0.0
            total_unpaid_salary = 0.0
            unpaid_ids = self.env['hr.leave'].search(
            [('employee_id', '=', x.employee_id.id), ('date_from', '>=', x.date_from),
             ('date_to', '<=', x.date_to), ('holiday_status_id.name', '=', 'Unpaid'), ('state', '=', 'validate')])
            if unpaid_ids:
                for leave in unpaid_ids:
                    # if worked_ids.code == 'Unpaid':
                    unpaid_sum += leave.number_of_days_temp
                employee_salary = x.employee_id.contract_id.wage
                total_unpaid_salary = employee_salary * unpaid_sum / 30
            x.unpaid_leave = total_unpaid_salary

    @api.depends('employee_id')
    def compute_month_lost_hours(self):
        sum_hours = 0.0
        for x in self:
            x.mon_lost_hours = 0
            employee_salary = x.contract_id.wage
            employee_salary_hour = employee_salary / 240
            lost_hour_ids = x.env['hr.attendance'].search(
                [('employee_id', '=', x.employee_id.id), ('write_date', '>=', x.date_from),
                 ('write_date', '<=', x.date_to)])
            for lost_h_sum in lost_hour_ids:
                sum_hours += lost_h_sum.lost_hours
            x.mon_lost_hours = sum_hours

    @api.depends('employee_id')
    def compute_month_overtime_hours(self):
        sum_hours = 0.0
        for x in self:
            x.overtime = 0
            employee_salary = x.contract_id.wage
            employee_salary_hour = employee_salary / 240
            # attendance = self.env['hr.attendance']
            overtime_ids = x.env['hr.overtime'].search(
                [('name', '=', x.employee_id.id), ('overtime_date', '>=', x.date_from),
                 ('overtime_date', '<=', x.date_to)])
            for overtime in overtime_ids:
                sum_hours += overtime.hour
                if overtime.is_working_day:
                    x.overtime = sum_hours * employee_salary_hour * 1.5
                if overtime.is_holiday:
                    x.overtime = sum_hours * employee_salary_hour * 2

    @api.depends('employee_id')
    def get_loan(self):
        for x in self:
            x.personal_loan = 0
            if x.employee_id:
                loan_ids = x.env['hr.loan.line'].search(
                    [('employee_id', '=', x.employee_id.id), ('paid', '=', False), ('paid_date', '>=', x.date_from),
                     ('paid_date', '<=', x.date_to), ('stop', '=', False)])
                for loan_id in loan_ids:
                    if loan_id.loan_id.state == 'done':
                        x.personal_loan = loan_id.paid_amount

    @api.depends('employee_id')
    def get_short_loan(self):
        for x in self:
            x.short_loan = 0
            if x.employee_id:
                amount = 0.00
                loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done'), ('date', '>=', x.date_from),
                     ('date', '<=', x.date_to)])
                for loan in loan_ids:
                    amount += loan.loan_amount
                x.short_loan = amount

    def action_payslip_done(self):
        for payslip in self:
            if payslip.employee_id:
                payslip_obj = payslip.search(
                    [('employee_id', '=', payslip.employee_id.id), ('name', '=', payslip.name), ('state', '=', 'done')])
                if payslip_obj:
                    raise Warning(_("This Employee Already Took This Month's Salary!"))
            loan_ids = payslip.env['hr.loan.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('paid', '=', False), ('stop', '=', False)])
            for line in loan_ids:
                if line.paid_date >= payslip.date_from and line.paid_date <= payslip.date_to and line.loan_id.state == 'done':
                    if not line.paid:
                        # line.payroll_id = payslip.id
                        line.action_paid_amount()
                else:
                    line.payroll_id = False

            short_loan_ids = payslip.env['hr.monthlyloan'].search(
                [('employee_id', '=', payslip.employee_id.id), ('state', '=', 'done'),
                 ('date', '>=', payslip.date_from),
                 ('date', '<=', payslip.date_to)])
            for short_loan in short_loan_ids:
                short_loan.action_paid()
        return super(Payslip, self).action_payslip_done()

    @api.constrains('name')
    def _no_duplicate_payslips(self):
        for rec in self:
            if self.employee_id:
                payslip_obj = self.search([('employee_id', '=', rec.employee_id.id), ('name', '=', rec.name),
                                           ('state', '=', 'done')])
                if payslip_obj:
                    raise Warning(_("This Employee Already Took his Month's Salary!"))


class MtwaHrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('close', 'Done'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    def close_payslip_run(self):
        for slip in self:
            for slip_run in slip.slip_ids:
                slip_run.action_payslip_done()
        return super(MtwaHrPayslipRun, self).close_payslip_run()

    def action_hr_confirm(self):
        for slip in self:
            slip.state = 'confirm'
            for slip_run in slip.slip_ids:
                slip_run.action_hr_confirm()

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_("Warning! You cannot delete a payslip which is in %s state.") % (rec.state))
        return super(MtwaHrPayslipRun, self).unlink()
