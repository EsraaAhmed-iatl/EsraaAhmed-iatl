from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, Warning
import babel
import time

from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class LtaTransport(models.Model):
    _name = 'lta.transport'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    date = fields.Date(string='Date', default=time.strftime('%Y-%m-15'), required=True)
    done_date = fields.Date(string='Approved Date')
    lta_transport_ids = fields.One2many('lta.transport.line', 'lta_transport_id', string='Transport and LTA')
    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    @api.onchange('date')
    def onchange_date(self):
        for x in self:
            ttyme = x.date
            locale = self.env.context.get('lang', 'en_US')
            x.name = _('Grant for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'
            for grant_id in rec.lta_transport_ids:
                grant_id.state = 'approve'

    def action_refuse(self):
        for rec in self:
            rec.state = 'refuse'
            for grant_id in rec.lta_transport_ids:
                grant_id.state = 'refuse'

    def action_reset(self):
        for rec in self:
            rec.state = 'draft'
            for grant_id in rec.lta_transport_ids:
                grant_id.state = 'draft'

    def action_done(self):
        amount_sum = 0.0
        for lta in self:
            lta_approve_date = fields.Date.today()
            journal_id = lta.journal_id.id
            reference = lta.name
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            for lta_transport_id in lta.lta_transport_ids:
                amount_sum += lta_transport_id.total_allowance

            lta_name = 'Transport and LTA payment of ' + reference
            move_dict = {
                'narration': reference,
                'ref': reference,
                'journal_id': journal_id,
                'date': lta_approve_date,
            }

            debit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.debit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount_sum > 0.0 and amount_sum or 0.0,
                'credit': amount_sum < 0.0 and -amount_sum or 0.0,
                'analytic_account_id': lta.analytic_debit_account_id.id,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.credit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount_sum < 0.0 and -amount_sum or 0.0,
                'credit': amount_sum > 0.0 and amount_sum or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            lta.write({'move_id': move.id, 'done_date': lta_approve_date})
            move.post()
        self.state = 'done'

    def unlink(self):
        for x in self:
            if any(x.filtered(lambda LtaTransport: LtaTransport.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete allowance & bonus batch which is not draft or refused!'))
            return super(LtaTransport, x).unlink()


class LtaTransportLine(models.Model):
    _name = 'lta.transport.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    contract_id = fields.Many2one('hr.contract', related='employee_id.contract_id', string='Contract')
    date = fields.Date(string='Date', default=time.strftime('%Y-%m-15'))
    done_date = fields.Date(string='Approved Date')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', readonly=True, string="Job Position")
    code = fields.Char(string='Code', related='employee_id.code', readonly=True)
    transport_allowance = fields.Float(string='Transport')
    lta_allowance = fields.Float('LTA', readonly=False)
    total_allowance = fields.Float('Total', compute='get_total_allowance')
    deduction = fields.Float(string='Deduction')
    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                related='department_id.analytic_debit_account_id',
                                                string="Analytic Account", readonly=True)
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    lta_transport_id = fields.Many2one('lta.transport', string='LTA Transport', ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'

    def action_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    def action_reset(self):
        for rec in self:
            rec.state = 'draft'

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        for rec in self:
            if rec.contract_id:
                rec.lta_allowance = rec.contract_id.wage * 6 / 12

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id.contract_id.transport_allowance:
            self.transport_allowance = self.employee_id.contract_id.transport_allowance

    @api.depends('transport_allowance', 'lta_allowance', 'deduction')
    def get_total_allowance(self):
        for rec in self:
            rec.total_allowance = rec.transport_allowance + rec.lta_allowance - rec.deduction

    def unlink(self):
        for x in self:
            if any(x.filtered(lambda LtaTransportLine: LtaTransportLine.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a allowance & LTA which is not draft or refused!'))
        return super(LtaTransportLine, self).unlink()

    def action_done(self):
        for lta in self:
            lta_approve_date = fields.Date.today()
            amount = lta.total_allowance
            lta_name = 'Transport and LTA Payment For ' + lta.employee_id.name
            reference = lta.name
            journal_id = lta.journal_id.id

            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            move_dict = {
                'narration': lta_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': lta_approve_date,
            }

            debit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.debit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': lta.analytic_debit_account_id.id,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.credit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            lta.write({'move_id': move.id, 'done_date': lta_approve_date})
            move.post()
        self.state = 'done'

    @api.onchange('employee_id', 'date')
    def onchange_employee(self):

        if (not self.employee_id) or (not self.date):
            return

        employee = self.employee_id
        date_from = self.date

        ttyme = date_from
        locale = self.env.context.get('lang', 'en_US')
        self.name = _('Transport and LTA allowance of %s for %s') % (
        employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))

    @api.constrains('name')
    def _no_duplicate_payslips(self):
        if self.employee_id:
            payslip_obj = self.search([('employee_id', '=', self.employee_id.id), ('name', '=', self.name),('state', '=', 'done')])
            if payslip_obj:
                raise Warning(_("This Employee Already Took his Month's Allowance!"))
