from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare

# from ii_hr_afi_15.models.is_hr_contract import create


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "HR Loan Request"

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    
    name = fields.Char(string="Loan Name", default="/", readonly=True)
    date = fields.Date(string="Date Request", default=fields.Date.today())
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True)
    parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    emp_salary = fields.Monetary(string="Employee Salary", related='employee_id.contract_id.wage', readonly=True)
    # loan_old_amount = fields.Float(string="Old Loan Amount Not Paid", compute='_get_old_loan')
    employee_account = fields.Many2one('account.account', string="Debit Account", readonly=True)
    loan_account = fields.Many2one('account.account', string="Credit Account")
    payment_account = fields.Many2one('account.account', string="Payment Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    attach = fields.Binary("Attachments", help="here you can attach a file or a document to the record !!")
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_amount')
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_amount')
    no_month = fields.Integer(string="No Of Month", default=1)
    payment_start_date = fields.Date(string="Start Date of Payment", required=True, default=fields.Date.today())
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    entry_count = fields.Integer(string="Entry Count", compute='compute_entery_count')
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    refund_move_id = fields.Many2one('account.move', string="Journal Refund Entry", readonly=True)
    refund_amount = fields.Float(string='Refund')
    refund_date = fields.Date(string="Date Refund", readonly=True)
    # paid_amount = fields.Float(string='Paid Value')
    state = fields.Selection(
        [('draft', 'To Submit'), ('approve', 'Approved'),
         ('confirm', 'Confirmed'), ('gm_approve', 'Confirmed'), ('done', 'Done'), ('refunded', 'Refunded'),
         ('refuse', 'Refused')],
        'Status', readonly=True, track_visibility='onchange', copy=False,
        help='The status is set to \'To Submit\', when a loan request is created.\
                  \nThe status is \'Confirmed\', when loan request is confirmed by department manager.\
                  \nThe status is \'Approved\', when loan request is confirmed by HR manager.\
                  \nThe status is \'Refused\', when loan request is refused by manager.\
                  \nThe status is \'Approved\', when loan request is approved by manager.', default='draft')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)

    def unlink(self):
        for x in self:
            if any(x.filtered(lambda hr_loan: hr_loan.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a Loan which is not draft or refused!'))
            return super(HrLoan, x).unlink()

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.long') or ' '
        res = super(HrLoan, self).create(values)
        return res

    def _compute_amount(self):
        total_paid_amount = 0.00
        for loan in self:
            loan.total_amount = 0
            loan.balance_amount = 0
            loan.total_paid_amount = 0
            for line in loan.loan_line_ids:
                if line.paid:
                    total_paid_amount += line.paid_amount

            balance_amount = loan.loan_amount - total_paid_amount
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid_amount
            # print self.balance_amount

    # @api.onchange('employee_id')
    # def _onchange_employee_d(self):
    #     for x in self:
    #         if x.employee_id:
    #             x.emp_salary = x.employee_id.contract_id.wage

    def loan_refuse(self):
        for x in self:
            x.state = 'refuse'

    def loan_reset(self):
        for x in self:
            x.state = 'draft'

    def loan_confirm(self):
        for x in self:
            # # schedule activity for Hr manager to approve
            # # get Direct manager group
            # fm_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Administrator'),
            #                                                     ('category_id', 'like', 'Employees')], limit=1).id
            #
            # # first of all get all Direct managers / advisors
            # self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))
            #
            # # schedule activity for Direct managers(s) to approve
            # for fm in list(filter(lambda x: (
            #         self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
            #                       self.env.cr.fetchall())):
            #     vals = {
            #         'activity_type_id': self.env['mail.activity.type'].sudo().search(
            #             [('name', 'like', 'Hr Loan')],
            #             limit=1).id,
            #         'res_id': self.id,
            #         'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'hr.loan')],
            #                                                            limit=1).id,
            #         'user_id': fm[0] or 1,
            #         'summary': self.name,
            #     }
            #
            #     # add lines
            #     self.env['mail.activity'].sudo().create(vals)
            x.state = 'approve'

    def loan_gm_approve(self):
        for x in self:
            x.state = 'gm_approve'

    def hr_validate(self):
        for x in self:
            x.state = 'confirm'

    @api.onchange('no_month')
    def validate_month(self):
        for x in self:
            if x.no_month < 1:
                raise Warning(_("Loan period can't be less than 1 month"))

            # return {'value':{'no_month':no_month}}

    def loan_validate(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        self.env.cr.execute("""select current_date;""")
        xt = self.env.cr.fetchall()
        self.comment_date4 = xt[0][0]
        if not self.employee_account or not self.loan_account or not self.journal_id:
            raise Warning(_("You must enter employee account & Loan account and journal to approve "))
        if not self.loan_line_ids:
            raise Warning(_('You must compute Loan Request before Approved'))
        can_close = False
        loan_obj = self.env['hr.loan']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        loan_ids = []
        for loan in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            loan_request_date = loan.date
            company_currency = loan.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = loan.loan_amount
            loan_name = 'Loan For ' + loan.employee_id.name
            reference = loan.name
            journal_id = loan.journal_id.id
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_request_date,
            }
            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': loan.employee_account.id,
                'journal_id': journal_id,
                'date': loan_request_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': loan.loan_account.id,
                'journal_id': journal_id,
                'date': loan_request_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_journal_credit = loan.journal_id.default_credit_account_id.id
                if not acc_journal_credit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                    loan.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_credit,
                    'journal_id': journal_id,
                    'date': loan_request_date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_journal_deit = loan.journal_id.default_debit_account_id.id
                if not acc_journal_deit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                    loan.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_deit,
                    'journal_id': journal_id,
                    'date': loan_request_date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            loan.write({'move_id': move.id, 'date': loan_request_date})
            move.post()
            self.state = 'done'

    def compute_loan_line(self):
        for loan in self:
            loan_line = self.env['hr.loan.line']
            loan_line.search([('loan_id', '=', self.id)]).unlink()
            date_start_str = loan.payment_start_date
            counter = 1
            amount_per_time = loan.loan_amount / loan.no_month
            for i in range(1, loan.no_month + 1):
                if i != loan.no_month:
                    line_id = loan_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2),
                        'employee_id': loan.employee_id.id,
                        'loan_id': loan.id})
                elif i == loan.no_month:
                    line_id = loan_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2) + round(
                            loan.loan_amount - (round(amount_per_time, 2) * loan.no_month), 2),
                        'employee_id': loan.employee_id.id,
                        'loan_id': loan.id})
                counter += 1
                date_start_str = date_start_str + relativedelta(months=1)

        return True

    @api.model
    def compute_entery_count(self):
        for loan in self:
            count = 0
            entry_count = loan.env['account.move.line'].search_count([('loan_id', '=', loan.id)])
            loan.entry_count = entry_count

    def button_reset_balance_total(self):
        total_paid_amount = 0.00
        for loan in self:
            for line in loan.loan_line_ids:
                if line.paid:
                    total_paid_amount += line.paid_amount
            balance_amount = loan.loan_amount - total_paid_amount
            self.write({'total_paid_amount': total_paid_amount, 'balance_amount': balance_amount})

    @api.constrains('employee_id')
    def _emp_loan_unpaid(self):
        for loan in self:
            if loan.employee_id:
                past_loans_ids = loan.env['hr.loan'].search(
                    [('employee_id', '=', loan.employee_id.id), ('state', '=', 'done')])
                for past_loans in past_loans_ids:
                    loan_line_ids = loan.env['hr.loan.line'].search([('loan_id', '=', past_loans.id)])
                    for loan_line in loan_line_ids:
                        if not loan_line.paid:
                            raise Warning(_(
                                "This employee must complete payments for a current running loan, in order to request another"))


class HrLoanLine(models.Model):
    _name = "hr.loan.line"
    _description = "HR Loan Request Line"
    _rec_name = "paid_date"

    paid_date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    paid_amount = fields.Float(string="Paid Amount", required=True)
    paid = fields.Boolean(string="Paid")
    notes = fields.Text(string="Notes")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", ondelete='cascade')
    payroll_id = fields.Many2one('hr.payslip', string="Payslip Ref.")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    stop = fields.Boolean(string="Stop")

    def action_paid_amount(self):
        for line in self:
            context = self._context
            can_close = False
            loan_obj = self.env['hr.loan']
            move_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            currency_obj = self.env['res.currency']
            created_move_ids = []
            loan_ids = []
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            if not line.payroll_id:
                if line.loan_id.state != 'done':
                    raise Warning(_("Loan Request must be approved"))
                paid_date = line.paid_date
                company_currency = line.employee_id.company_id.currency_id.id
                current_currency = self.env.user.company_id.currency_id.id
                debit_account = False
                amount = line.paid_amount
                loan_name = 'Installment Payment of '+line.loan_id.employee_id.name
                reference = line.loan_id.name
                journal_id = line.loan_id.journal_id.id
                if line.loan_id.payment_account.id:
                    debit_account = line.loan_id.payment_account.id
                if not line.loan_id.payment_account.id:
                    debit_account = line.loan_id.loan_account.id

                debit_line = (0, 0, {
                    'name': loan_name,
                    'ref': reference,
                    'account_id': debit_account,
                    'journal_id': journal_id,
                    'analytic_account_id': False,
                    'date': paid_date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'loan_id': line.loan_id.id,

                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                credit_line = (0, 0, {
                    'name': loan_name,
                    'ref': reference,
                    'account_id': line.loan_id.employee_account.id,
                    'journal_id': journal_id,
                    'analytic_account_id': False,
                    'date': paid_date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'loan_id': line.loan_id.id,

                })
                line_ids.append(credit_line)
                move_dict = {
                             'narration': loan_name,
                             'ref': reference,
                             'journal_id': journal_id,
                             'date': fields.Date.today(),
                             'line_ids': line_ids
                             }
                move = self.env['account.move'].create(move_dict)
                move.post()
                self.write({'paid': True, 'move_id': move.id, 'notes': 'Paid'})
        return True

    @api.constrains('paid_amount')
    def _loan_line_installment(self):
        for x in self:
            if x.paid_amount:
                short_loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done')])
                short_loan_amt = 0.00
                for loan in short_loan_ids:
                    DATETIME_FORMAT = "%Y-%m-%d"
                    short_loan_date = loan.date
                    installment_loan_date = x.paid_date
                    if short_loan_date.month == installment_loan_date.month:
                        short_loan_amt += loan.loan_amount
                if x.paid_amount + short_loan_amt > x.loan_id.emp_salary * 0.8:
                    raise UserError(_("Monthly Loan  Cannot Exceed 70%% of The Employee's Salary!"))
            else:
                short_loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done')])
                short_loan_amt = 0.00
                for loan in short_loan_ids:
                    DATETIME_FORMAT = "%Y-%m-%d"
                    short_loan_date = datetime.strptime(loan.date, DATETIME_FORMAT)
                    installment_loan_date = datetime.strptime(x.paid_date, DATETIME_FORMAT)
                    if short_loan_date.month == installment_loan_date.month:
                        short_loan_amt += loan.loan_amount
                if x.paid_amount + short_loan_amt > x.loan_id.emp_salary:
                    raise UserError(_("Monthly Loan Cannot Exceed The Employee's Salary!"))


class HrMonthlyloan(models.Model):
    _name = 'hr.monthlyloan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    name = fields.Char('Loan')
    date = fields.Date(string="loan Date", default=fields.Date.today())
    date_pay = fields.Date(string="Loan Pay Date", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    employee_salary = fields.Float(string="Employee Salary", compute='_compute_salary')
    employee_account = fields.Many2one('account.account', string="Debit Account")
    loan_account = fields.Many2one('account.account', string="Credit Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    move_id_pay = fields.Many2one('account.move', string="Loan Payment Entry", readonly=True)
    payment_account = fields.Many2one('account.account', string="Payment Account")
    state = fields.Selection(
        [('draft', 'To Submit'), ('confirm', 'To Approve'),
         ('approve', 'Approved by HR'), ('done', 'Done'), ('paid', 'Paid'),
         ('refuse', 'Refused')],
        'Status', default='draft', readonly=True)

    def loan_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def loan_approve(self):
        for rec in self:
            rec.state = 'approve'

    def action_paid(self):
        for loan in self:
            if loan.state == 'done':
                loan_pay_date = fields.Date.today()
                amount = loan.loan_amount
                loan_name = 'Short Loan Payment For ' + loan.employee_id.name
                reference = loan.name
                journal_id = loan.journal_id.id
                if loan.payment_account.id:
                    debit_account = loan.payment_account.id
                if not loan.payment_account.id:
                    debit_account = loan.loan_account.id
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                move_dict = {
                    'narration': loan_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                }

                debit_line = (0, 0, {
                    'name': loan_name,
                    'partner_id': False,
                    'account_id': debit_account,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'analytic_account_id': False,
                    'tax_line_id': 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                credit_line = (0, 0, {
                    'name': loan_name,
                    'partner_id': False,
                    'account_id': loan.employee_account.id,
                    'journal_id': journal_id,
                    'date': loan_pay_date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'analytic_account_id': False,
                    'tax_line_id': 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                loan.write({'move_id_pay': move.id, 'date_pay': loan_pay_date})
                move.post()
        self.state = 'paid'

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.short') or ' '
        res = super(HrMonthlyloan, self).create(values)
        return res

    @api.depends('employee_id')
    def _compute_salary(self):
        for rec in self:
            rec.employee_salary = 0
        if rec.employee_id:
            rec.employee_salary = rec.employee_id.contract_id.wage

    def loan_validate(self):
        if not self.employee_account or not self.loan_account or not self.journal_id:
            raise Warning(_("You must enter employee account & Loan account and journal to approve "))
        for monthh_loan in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            loan_date = monthh_loan.date
            amount = monthh_loan.loan_amount
            employee_salary = self.employee_id.contract_id.wage
            if amount > employee_salary / 2:
                raise Warning(_("Loan should not exceed half of employee salary"))
            loan_name = 'Short Loan For ' + monthh_loan.employee_id.name
            reference = monthh_loan.name
            journal_id = monthh_loan.journal_id.id
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_date,
            }
            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': monthh_loan.employee_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': monthh_loan.loan_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            monthh_loan.write({'move_id': move.id, 'date': loan_date})
            move.post()
            self.state = 'done'

    @api.constrains('loan_amount')
    def _loan_amount(self):
        if self.loan_amount:
            salary = self.employee_salary
            allowable_loan = salary * 70 / 100
            if self.loan_amount > allowable_loan:
                raise Warning(_("Monthly Loan Cannot Exceed 70% of The Employee's Salary!"))

    def loan_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    def loan_reset(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_("Warning! You cannot delete a Loan which is in %s state.") % (rec.state))
            return super(HrMonthlyloan, self).unlink()


class WizardLoan(models.Model):
    _name = 'wizard.loan'
    _description = 'Pay Loan'
    loan_id = fields.Many2one('hr.loan', 'Loan', ondelete='cascade')
    refund_amount = fields.Float('Refund')

    def refund_loan(self):
        for loan in self:
            if loan.loan_id:
                refund_amount = loan.refund_amount
                hr_loan_id = loan.loan_id
                unpaid_amount = hr_loan_id.balance_amount
                total_amount = hr_loan_id.loan_amount
                reaming_amount = unpaid_amount - refund_amount
                if reaming_amount == 0:
                    if hr_loan_id.state == 'done':
                            loan_amount = 0.0
                            acc_journal_credit = hr_loan_id.journal_id.default_credit_account_id.id
                            acc_journal_debit = hr_loan_id.journal_id.default_credit_account_id.id
                            if not acc_journal_credit:
                                raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                    hr_loan_id.journal_id.name))

                            precision = self.env['decimal.precision'].precision_get('Payroll')
                            self.env.cr.execute("""select current_date;""")
                            xt = self.env.cr.fetchall()
                            self.comment_date4 = xt[0][0]
                            loan_line_ids = hr_loan_id.loan_line_ids
                            for loan_line in loan_line_ids:
                                paid = loan_line.paid
                                if not paid:
                                    loan_line.paid = True
                                    created_move_ids = []
                                    loan_ids = []
                                    line_ids = []
                                    debit_sum = 0.0
                                    credit_sum = 0.0
                                    refund_date = fields.Date.today()
                                    journal_id = hr_loan_id.journal_id.id
                                    company_currency = hr_loan_id.employee_id.company_id.currency_id.id
                                    current_currency = hr_loan_id.env.user.company_id.currency_id.id
                                    ref_loan_name = 'Refund Loan For ' + hr_loan_id.employee_id.name
                                    reference = 'Refund Loan'
                                    move_dict = {
                                        'narration': ref_loan_name,
                                        'ref': reference,
                                        'journal_id': journal_id,
                                        'date': refund_date,
                                    }
                                    debit_line = (0, 0, {
                                        'name': ref_loan_name,
                                        'partner_id': False,
                                        'account_id': hr_loan_id.loan_account.id,
                                        'journal_id': journal_id,
                                        'date': refund_date,
                                        'debit': unpaid_amount > 0.0 and unpaid_amount or 0.0,
                                        'credit': unpaid_amount < 0.0 and -unpaid_amount or 0.0,
                                        'analytic_account_id': False,
                                        'tax_line_id': 0.0,
                                    })
                                    line_ids.append(debit_line)
                                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                                    credit_line = (0, 0, {
                                        'name': ref_loan_name,
                                        'partner_id': False,
                                        'account_id': hr_loan_id.employee_account.id,
                                        'journal_id': journal_id,
                                        'date': refund_date,
                                        'debit': unpaid_amount < 0.0 and -unpaid_amount or 0.0,
                                        'credit': unpaid_amount > 0.0 and unpaid_amount or 0.0,
                                        'analytic_account_id': False,
                                        'tax_line_id': 0.0,
                                    })
                                    line_ids.append(credit_line)
                                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                                        adjust_credit = (0, 0, {
                                            'name': _('Adjustment Entry'),
                                            'partner_id': False,
                                            'account_id': acc_journal_debit,
                                            'journal_id': journal_id,
                                            'date': refund_date,
                                            'debit': 0.0,
                                            'credit': debit_sum - credit_sum,
                                        })
                                        line_ids.append(adjust_credit)

                                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                                        if not acc_journal_debit:
                                            raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                                hr_loan_id.journal_id.name))
                                        adjust_debit = (0, 0, {
                                            'name': _('Adjustment Entry'),
                                            'partner_id': False,
                                            'account_id': acc_journal_credit,
                                            'journal_id': journal_id,
                                            'date': refund_date,
                                            'debit': credit_sum - debit_sum,
                                            'credit': 0.0,
                                        })
                                        line_ids.append(adjust_debit)
                                    move_dict['line_ids'] = line_ids
                                    move = loan.env['account.move'].create(move_dict)
                                    hr_loan_id.write({'refund_move_id': move.id, 'refund_date': refund_date,
                                                      'state': 'refunded'})
                                    move.post()
                else:
                    raise UserError(_('You Have To Refund %s') % unpaid_amount)


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    loan_id = fields.Many2one('hr.loan', string="Loan", ondelete='cascade')
