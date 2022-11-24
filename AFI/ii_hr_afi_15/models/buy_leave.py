# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, fields, api, exceptions, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError


class BuyLeave(models.Model):
    _name = 'buy.leave'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )
    manager_id = fields.Many2one('res.users', string="Manager", required=False, )
    remaining_leaves = fields.Float(string="Leave Balance",
                                    readonly=True,
                                    compute='calculate_buy_leave', store=True
                                    )
    wage = fields.Float(string="Wage",
                        readonly=True,
                        compute='calculate_buy_leave',
                        store=True
                        )
    days = fields.Float(string="Days", required=False, )
    amount = fields.Float(string="Amount", required=False,
                          compute='calculate_buy_leave', store=True
                          )
    date = fields.Date(string="Date", required=False, default=fields.Date.context_today)
    state = fields.Selection(string="State",
                             selection=[
                                 ('draft', 'draft'),
                                 ('direct_manager', 'Direct Manager'),
                                 ('hr', 'HR'),
                                 ('done', 'Done'),
                             ], default='draft',
                             required=False, )

    department_approve = fields.Boolean('Approve', compute='_get_approve')

    @api.depends('manager_id', 'state')
    def _get_approve(self):
        for rec in self:
            rec.department_approve = False
            if rec.state == 'direct_manager' and rec.manager_id.id == self.env.user.id:
                rec.department_approve = True

    def action_sent_to_direct_manager(self):
        self.state = 'direct_manager'

    def action_direct_manager_approve(self):
        self.state = 'hr'

    def action_create_finance_approve(self):
        self.bntton_done()
        if self.button_create_payment(self.amount, self.employee_id, self.date):
            self.state = 'done'

    def bntton_done(self):
        res = self.env['hr.leave.type'].search([('name', '=', 'Paid Time Off')])
        for rec in self:
            create_leave = self.env['hr.leave.allocation'].create({
                'name': 'Buy Leave',
                'employee_id': rec.employee_id.id,
                'holiday_status_id': res.id,
                'allocation_type': 'regular',
                'number_of_days': -int(rec.days)
            })
            create_leave.action_confirm()
            create_leave.action_validate()

    @api.depends('employee_id', 'days')
    def calculate_buy_leave(self):
        for rec in self:
            if rec.employee_id:
                rec.remaining_leaves = rec.employee_id.remaining_leaves
                rec.wage = rec.employee_id.contract_id.wage
                rec.manager_id = rec.employee_id.user_id.id
            if rec.days:
                rec.amount = (rec.days / 30) * rec.wage

    def button_create_payment(self, amount, employee_id, fa_date):
        if amount > 0.0 and employee_id:
            res = self.env['finance.approval'].create({
                'request_amount': amount,
                'fa_date': fa_date,
                'reason': 'Buy Leave ' + employee_id.name,
            })
            return res
        else:
            raise ValidationError(_('Enter Amount ...'))


class hrLeaveAllocationInherit(models.Model):
    _inherit = 'hr.leave.allocation'

    _sql_constraints = [
        ('type_value',
         "CHECK( (holiday_type='employee' AND (employee_id IS NOT NULL OR multi_employee IS TRUE)) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL))",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('duration_check',
         "CHECK( ( number_of_days <= 0 AND allocation_type='regular') or (allocation_type != 'regular'))",
         "The duration must be greater than 0.")
    ]
