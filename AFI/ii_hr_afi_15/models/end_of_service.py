from datetime import datetime

from odoo import models, fields, api, exceptions, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date


class End_Of_Service(models.Model):
    _name = 'end.of.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    def get_end_service_count(self):
        count = self.env['finance.approval'].search_count([('end_service_id', '=', self.id)])
        self.end_service_count = count

    def open_end_service(self):
        return {
            'name': _('End Service'),
            'view_type': 'form',
            'res_model': 'finance.approval',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('end_service_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )

    end_service_count = fields.Integer(compute=get_end_service_count, )

    working_year = fields.Float(string="Working Years",
                                compute='calculate_leave', store=True,
                                required=False, )
    working_month = fields.Char(string="Working Month",
                                compute='calculate_leave', store=True,
                                required=False, )

    remaining_leaves = fields.Float(string="Leave Balance",
                                    readonly=True,
                                    compute='calculate_leave', store=True
                                    )

    total_unpaid_loan_amount = fields.Float(string="Total Unpaid Loan Amount",
                                            readonly=True,
                                            compute='calculate_leave', store=True
                                            )
    amount_leave_balance = fields.Float(string="Amount Leave balance",
                                        readonly=True,
                                        compute='calculate_leave', store=True
                                        )

    total_end_of_service_amount = fields.Float(string="Total End Of Service Amount ",
                                               readonly=True,
                                               compute='calculate_leave', store=True
                                               )
    benefits = fields.Float(string="Benefits",
                            compute='calculate_leave', store=True)
    state = fields.Selection(string="State",
                             selection=[('draft', 'Draft'),
                                        ('approve', 'Approve'),
                                        ('done', 'Done'),
                                        ('reject', 'Reject'),
                                        ], default='draft', required=False, )
    date = fields.Date(string="Date", required=False, default=fields.Date.context_today)

    def send_to_approve(self):
        self.state = 'approve'

    def action_approve(self):
        res = self.button_create_payment(self.total_end_of_service_amount, self.employee_id, self.date)
        if res:
            self.state = 'done'

    def action_reject(self):
        self.state = 'reject'

    def button_create_payment(self, amount, employee_id, fa_date):
        if amount > 0.0 and employee_id:
            res = self.env['finance.approval'].create({
                'request_amount': amount,
                'fa_date': fa_date,
                'end_service_id': self.id,
                'reason': 'End Service ' + employee_id.name,
            })
            return res
        else:
            raise ValidationError(_('Enter Amount ...'))

    @api.depends('employee_id')
    def calculate_leave(self):
        for rec in self:
            sum_year = 0.0
            sum_month = 0.0
            sum_loan = 0.0
            rec.remaining_leaves = rec.employee_id.remaining_leaves
            if rec.employee_id:
                if rec.employee_id.contract_id.state == 'open':
                    if rec.employee_id.hiring_date:
                        sum_year = relativedelta(date.today(), rec.employee_id.hiring_date).years
                        sum_month = relativedelta(date.today(), rec.employee_id.hiring_date).months
                rec.working_year = sum_year
                rec.working_month = 'Years : '+str(sum_year )+' Months : '+str(sum_month)
            result = self.env['hr.loan'].search([('employee_id', '=', rec.employee_id.id)])
            if result:
                for line in result:
                    sum_loan += line.balance_amount
                rec.total_unpaid_loan_amount = sum_loan
            if rec.remaining_leaves:
                rec.amount_leave_balance = (rec.remaining_leaves / 30) * rec.employee_id.contract_id.wage
            if rec.working_year:
                if rec.working_year >= 1 and rec.working_year <= 5:
                    rec.benefits = rec.employee_id.contract_id.wage * 2
                elif rec.working_year >= 6 and rec.working_year <= 10:
                    rec.benefits = rec.employee_id.contract_id.wage * 3

                elif rec.working_year >= 11 and rec.working_year <= 15:
                    rec.benefits = rec.employee_id.contract_id.wage * 5

                elif rec.working_year >= 16 and rec.working_year <= 20:
                    rec.benefits = rec.employee_id.contract_id.wage * 7

                elif rec.working_year >= 20:
                    rec.benefits = rec.employee_id.contract_id.wage * 10
            if (rec.amount_leave_balance and rec.benefits) or rec.total_unpaid_loan_amount:
                rec.total_end_of_service_amount = rec.amount_leave_balance + rec.benefits - rec.total_unpaid_loan_amount


class FinanceApproveInherit(models.Model):
    _inherit = 'finance.approval'

    end_service_id = fields.Many2one(comodel_name="end.of.service", string="", required=False, )
