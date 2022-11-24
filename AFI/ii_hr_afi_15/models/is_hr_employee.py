from odoo import api, fields, models, _
import datetime
from odoo.exceptions import UserError


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    contract_id = fields.Many2one(readonly=True)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _compute_loans(self):
        for x in self:
            count = 0
            loan_remain_amount = 0.00
            loan_ids = x.env['hr.loan'].search([('employee_id', '=', x.id)])
            for loan in loan_ids:
                loan_remain_amount += loan.balance_amount
                count += 1
            x.loan_count = count
            x.loan_amount = loan_remain_amount

    is_manager = fields.Boolean(string="Is Manager", groups="hr.group_hr_user")
    loan_amount = fields.Float(string="loan Amount", compute='_compute_loans', groups="hr.group_hr_user")
    loan_count = fields.Integer(string="Loan Count", compute='_compute_loans', groups="hr.group_hr_user")
    hiring_date = fields.Date(string="Date of Joining", groups="hr.group_hr_user")
    quit_date = fields.Date(string="Date of Quit", groups="hr.group_hr_user")
    leave_balance = fields.Float(string='Leave Balance', compute='_compute_leave_balance', groups="hr.group_hr_user")
    annual_leave = fields.Float(string="Annual Leave", groups="hr.group_hr_user")
    blood = fields.Selection([('o1', 'O+'), ('o2', 'O-'), ('a1', 'A+'),('a2', 'A-'),('b1', 'B+'),('b2', 'B-'),
                              ('ab1', 'AB+'), ('ab2', 'AB-')], groups="hr.group_hr_user")
    mother_name = fields.Char(string='Mother Name', groups="hr.group_hr_user")
    code = fields.Char(string='Employee Code', groups="hr.group_hr_user")
    national_service_from = fields.Date(string='Date From', groups="hr.group_hr_user")
    national_service_to = fields.Date(string='Date To', groups="hr.group_hr_user")
    graduation_year = fields.Date(string='Graduation Year', groups="hr.group_hr_user")
    signature = fields.Binary(string='Signature', groups="hr.group_hr_user")
    year_experience = fields.Integer(string='Years of Experience', groups="hr.group_hr_user")
    month_experience = fields.Integer(string='Months of Experience', groups="hr.group_hr_user")
    age_in_years = fields.Integer(string='Age In Years', compute='_calculate_age', groups="hr.group_hr_user")
    family_member = fields.Integer(string='No Of Family Members', groups="hr.group_hr_user")
    edu_level_id = fields.Many2one('educational.level', string='Degree', groups="hr.group_hr_user")
    edu_section_id = fields.Many2one('education.section', string='Section',
                                     domain="[('education_level_id', '=', edu_level_id)]", groups="hr.group_hr_user")
    age = fields.Char(compute='_calculate_age', string='Age', groups="hr.group_hr_user")

    @api.depends('remaining_leaves')
    def _compute_leave_balance(self):
        for leave in self:
            leave.leave_balance = 0
            if leave.remaining_leaves:
                remaining_leaves = leave.remaining_leaves
                leave.leave_balance = remaining_leaves

    @api.depends('birthday')
    def _calculate_age(self):
        str_now = datetime.datetime.now().date()
        age = ''
        employee_years = 0
        for employee in self:
            if employee.birthday:
                date_start = datetime.datetime.strptime(str(employee.birthday), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                remaining_days = total_days - 365 * employee_years
                employee_months = int(12 * remaining_days / 365)
                employee_days = int(0.5 + remaining_days - 365 * employee_months / 12)
                age = str(employee_years) + ' Year(s) ' + str(employee_months) + ' Month(s) ' + str(
                    employee_days) + ' day(s)'
            employee.age = age
            employee.age_in_years = employee_years


class EduactionSection(models.Model):
    _name = 'education.section'
    name = fields.Char(string='Section')
    education_level_id = fields.Many2one('educational.level',string='Level')


class EducationalLevel(models.Model):
    _name = 'educational.level'
    name = fields.Char(string='Educational Level')
    edu_section_ids = fields.One2many('education.section','education_level_id', string='Section')


class Department(models.Model):
    _inherit = 'hr.department'
    analytic_debit_account_id = fields.Many2one('account.analytic.account', string="Department Debit Analytic Account")
