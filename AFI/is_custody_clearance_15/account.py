#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Custody Clearance                                          #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from datetime import datetime
from . import amount_to_ar
from odoo.exceptions import except_orm, Warning, ValidationError


################################
# add custody clearance approval
class custody_clearance(models.Model):
    _name = 'custody.clearance'
    _description = 'A model for tracking custody clearance.'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'clearance_no'

    clearance_no = fields.Char('Clearance No.', help='Auto-generated Clearance No. for custody clearances')
    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    cc_date = fields.Date('Date')
    requester = fields.Char('Requester', required=True, default=lambda self: self.env.user.name)

    approval_id = fields.Many2one('finance.approval', 'Approval Reference')
    clearance_amount_new = fields.Float(compute='approval_reference', string='Requested Amount', store=True, )
    clearance_amount = fields.Float('Requested Amount', required=True)
    clearance_currency = fields.Many2one('res.currency', 'Currency',
                                         default=lambda self: self.env.user.company_id.currency_id)
    difference_amount = fields.Float('Difference Amount', readonly=True)
    clearance_amount_words = fields.Char(string='Amount in Words', readonly=True, default=False, copy=False,
                                         compute='_compute_text', translate=True)
    reason = fields.Char('Reason')
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'),
                              ('fm_app', 'Financial Approval'),
                              ('au_app', 'Auditor Approval'),
                              ('reject', 'Rejected'),
                              ('validate', 'Validated')],
                             string='Custody Clearance Status', default='draft')
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain=[('type', 'in', ['bank', 'cash'])])
    clearance_journal_id = fields.Many2one('account.journal', 'Clearance Journal', help='Clearance Journal')
    cr_account = fields.Many2one('account.account', string="Credit Account")
    move_id = fields.Many2one('account.move', 'Clearance Journal Entry', readonly=True, copy=False)
    move2_id = fields.Many2one('account.move', 'Payment/Receipt Journal Entry', readonly=True, copy=False)
    mn_remarks = fields.Text('Manager Remarks')
    auditor_remarks = fields.Text('Reviewer Remarks')
    fm_remarks = fields.Text('Finance Man. Remarks')
    view_remarks = fields.Text('View Remarks', readonly=True, compute='_get_remarks', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    manager_id = fields.Many2one('res.users', string='Manager')
    mn_app_id = fields.Many2one('res.users', string="Manager Approval By")
    au_app_id = fields.Many2one('res.users', string="Reviewer Approval By")
    fm_app_id = fields.Many2one('res.users', string="Financial Approval By")
    at_app_id = fields.Many2one('res.users', string="Validated By")
    # add company_id to allow this module to support multi-company
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    # link with finance approval
    # finance_approval_id = fields.Many2one('finance.approval', 'Finance Approval No.')
    # clearance lines
    custody_clearance_line_ids = fields.One2many('custody.clearance.line', 'custody_clearance_id',
                                                 string='Clearance Details')

    department_id = fields.Many2one('hr.department', 'Department')
    beneficiary_id = fields.Many2one(comodel_name="res.partner",
                                     string="Beneficiary",
                                     readonly=True,
                                     required=False, )

    @api.onchange('approval_id')
    def get_approval_id(self):
        for rec in self:
            if rec.approval_id.beneficiary_id.id:
                rec.beneficiary_id = rec.approval_id.beneficiary_id.id

    @api.onchange('approval_id')
    def onchange_finance_approval_id(self):
        if self.approval_id:
            self.clearance_currency = self.approval_id.request_currency.id
            # print self.approval_id.request_amount
            self.clearance_amount = self.approval_id.request_amount

    @api.depends('approval_id', )
    def approval_reference(self):
        approve_obj = self.env['finance.approval'].search([('id', '=', self.approval_id.id),
                                                           ('state', '=', 'validate')])
        custody_obj = self.env['custody.clearance'].search([('approval_id', '=', self.approval_id.id),
                                                            ('state', '=', 'validate')])
        # raise ValidationError(approve_obj)
        result = 0
        if not approve_obj:
            self.clearance_amount_new = approve_obj.request_amount

        if not custody_obj:
            self.clearance_amount_new = approve_obj.request_amount
        if approve_obj:
            for i in approve_obj:
                f = i.request_amount
                for c in custody_obj:
                    result += c.clearance_amount
                self.clearance_amount_new = f - result

    # Generate name of custody automatically
    @api.depends('clearance_no', 'requester', 'clearance_amount')
    def _get_description(self):
        self.name = (self.clearance_no and ("Clearance No: " + str(self.clearance_no)) or " ") + "/" + (
                self.requester and ("Requester: " + self.requester) or " ") + "/" \
                    + (self.clearance_amount and ("Clearance Amount: " + str(self.clearance_amount)) or " ") + "/" + (
                            self.reason and ("Reason: " + self.reason) or " ")

    # # Return clearance amount in words
    # @api.depends('clearance_amount', 'clearance_currency')
    # def _compute_text(self):
    #     self.clearance_amount_words = amount_to_ar.amount_to_text_ar(self.clearance_amount,
    #                                                                  self.clearance_currency.narration_ar_un,
    #                                                                  self.clearance_currency.narration_ar_cn)

    # Return request amount in words
    @api.depends('clearance_amount', 'clearance_currency')
    def _compute_text(self):
        from . import money_to_text_ar
        for r in self:
            r.clearance_amount_words = money_to_text_ar.amount_to_text_arabic(r.clearance_amount,
                                                                              r.clearance_currency.name)

    # Generate remarks
    @api.depends('mn_remarks', 'auditor_remarks', 'fm_remarks')
    def _get_remarks(self):
        self.view_remarks = (self.mn_remarks and ("Manager Remarks: " + str(self.mn_remarks)) or " ") + "\n\n" + (
                self.auditor_remarks and ("Reviewer Remarks: " + str(self.auditor_remarks)) or " ") + "\n\n" + (
                                    self.fm_remarks and ("Financial Man. Remarks: " + self.fm_remarks) or " ")

    # overriding default get
    @api.model
    def default_get(self, fields):
        res = super(custody_clearance, self).default_get(fields)
        # get manager user id
        manager = self.env['res.users'].search([('id', '=', self.env.user.id)], limit=1).approval_manager.id
        if manager:
            res.update({'manager_id': manager})
        return res

    # overriding create to save number with commit
    @api.model
    def create(self, vals):
        res = super(custody_clearance, self).create(vals)
        # get custody clearance sequence no.
        next_seq = self.env['ir.sequence'].get('custody.clearance.sequence')
        res.update({'clearance_no': next_seq})
        return res

    # added to allow for custody clearance
    def to_approve(self):
        # schedule activity for manager to approve
        fm_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Accountant')], limit=1).id

        # first of all get all finance managers / advisors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))

        # schedule activity for advisor(s) to approve
        for fm in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                              self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.sudo().env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': fm[0] or 1,
                'summary': self.name,
            }
            #
            #     # add lines
            self.env['mail.activity'].sudo().create(vals)

        # change state
        self.state = 'fm_app'
        return True

    # manager approval
    def manager_approval(self):
        # get auditor group
        auditor_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Direct Manager')], limit=1).id

        # first of all get all auditors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (auditor_group_id))

        # schedule activity for auditor(s) to approve
        for auditor in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                                   self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': auditor[0] or 1,
                'summary': self.name,
            }
            #
            #     # add lines
            self.env['mail.activity'].sudo().create(vals)

        # change state
        # self.state = 'au_app'
        self.mn_app_id = self.env.user.id

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    # auditor approval
    def fm_approval(self):
        # get finance manager group
        fm_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Direct Manager')], limit=1).id

        # first of all get all finance managers / advisors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))

        # schedule activity for advisor(s) to approve
        for fm in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                              self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.sudo().env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': fm[0] or 1,
                'summary': self.name,
            }
            #
            #     # add lines
            self.env['mail.activity'].sudo().create(vals)

        # change state
        self.state = 'fm_app'
        self.fm_app_id = self.env.user.id

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def au_approval(self):
        # schedule activity for finance manager to approve
        # get Direct manager group
        fm_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Account Auditor')], limit=1).id

        # first of all get all Direct managers / advisors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))

        # schedule activity for Direct managers(s) to approve
        for fm in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                              self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': fm[0] or 1,
                'summary': self.name,
            }

            # add lines
            self.env['mail.activity'].sudo().create(vals)
        # change state
        self.state = 'au_app'
        return True

    # reject custody approval
    def reject(self):
        self.state = 'reject'

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    # validate, i.e. post to account moves
    @api.model
    def get_currency(self, line=None, total=None):
        if total:
            return total / self.clearance_currency.rate
        if self.clearance_currency != self.env.user.company_id.currency_id:
            return line.amount / self.clearance_currency.rate
        else:
            return line.amount

    # schedule activity to accountant to validate
    def schedule_fm(self):
        # get accountant/validator group
        at_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Validator')], limit=1).id

        # first of all get all finance managers / advisors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (at_group_id))

        # schedule activity for advisors(s) to validate
        for at in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                              self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': at[0] or 1,
                'summary': self.name,
            }

            # add lines
            self.env['mail.activity'].sudo().create(vals)

    # validate and check difference
    def validate(self):
        if not self.clearance_journal_id:
            raise Warning(_("Clearance journal must be selected!"))
        if not self.journal_id:
            raise Warning(_("Payment journal must be selected!"))
        if not self.cr_account:
            raise Warning(_("Credit account must be selected!"))

        #################
        # clearance part #
        #################
        # account move entry
        db_total = 0
        entries = []
        for line in self.custody_clearance_line_ids:
            if not line.exp_account:
                raise ValidationError(_("Please select account!"))

            debit_val = {
                'move_id': self.move_id.id,
                'name': line.name,
                'account_id': line.exp_account.id,
                'debit': self.get_currency(line),
                'analytic_account_id': line.analytic_account.id,
                'currency_id': (self.clearance_currency != self.env.user.company_id.currency_id)
                               and self.clearance_currency.id or None,
                'amount_currency': (self.clearance_currency != self.env.user.company_id.currency_id) and line.amount
                                   or None,
                'company_id': self.company_id.id,
            }
            entries.append((0, 0, debit_val))
            db_total += line.amount

        # create credit entry which is total of debit
        credit_val = {
            'move_id': self.move_id.id,
            'name': line.name,
            'account_id': self.cr_account.id,
            'credit': self.get_currency(total=db_total),
            'currency_id': (self.clearance_currency != self.env.user.company_id.currency_id)
                           and self.clearance_currency.id or None,
            'amount_currency': (self.clearance_currency != self.env.user.company_id.currency_id) and -(db_total)
                               or None,
            'company_id': self.company_id.id,
        }
        entries.append((0, 0, credit_val))

        vals = {
            'journal_id': self.clearance_journal_id.id,
            'date': self.cc_date,
            'customer_name': self.requester,
            'ref': self.clearance_no,
            'company_id': self.company_id.id,
            'line_ids': entries,
        }

        self.move_id = self.env['account.move'].create(vals)

        ##################
        # difference part#
        ##################
        # get difference
        self.difference_amount = self.clearance_amount - db_total
        if self.difference_amount == 0:
            # Change state if all went well!
            self.schedule_fm()
            self.state = 'validate'
            self.at_app_id = self.env.user.id

            # Update footer message
            message_obj = self.env['mail.message']
            message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
            msg_id = self.message_post(body=message)
            self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        # difference greater
        elif self.difference_amount > 0:
            # account move entry
            if self.clearance_currency == self.env.user.company_id.currency_id:
                temp_move_line_db = {
                    'move_id': self.move2_id.id,
                    'name': self.name + ": Receipt of difference",
                    'account_id': self.journal_id.default_account_id.id,
                    'debit': self.difference_amount,
                    'company_id': self.company_id.id,
                }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.cr_account.id,
                                     'credit': self.difference_amount,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': self.cc_date,
                                     'ref': self.clearance_no,
                                     'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'validate'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search(
                    [('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            elif self.clearance_currency != self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.journal_id.default_account_id.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': self.difference_amount,
                                     'debit': self.difference_amount / self.clearance_currency.rate,
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.cr_account.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': -self.difference_amount,
                                     'credit': self.difference_amount / self.clearance_currency.rate,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': self.cc_date,
                                     'ref': self.clearance_no,
                                     'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }

                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'validate'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search(
                    [('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            else:
                raise Warning(_("An issue was faced when validating difference!"))
        # difference less
        elif self.difference_amount < 0:
            # account move entry
            if self.clearance_currency == self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.cr_account.id,
                                     'debit': abs(self.difference_amount),
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.journal_id.default_account_id.id,
                                     'credit': abs(self.difference_amount),
                                     'company_id': self.company_id.id,
                                     }

                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': self.cc_date,
                                     'ref': self.clearance_no,
                                     'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'validate'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search(
                    [('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            elif self.clearance_currency != self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.cr_account.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': abs(self.difference_amount),
                                     'debit': abs(self.difference_amount) / self.clearance_currency.rate,
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.journal_id.default_account_id.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': -(abs(self.difference_amount)),
                                     'credit': abs(self.difference_amount) / self.clearance_currency.rate,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': self.cc_date,
                                     'customer_name': self.requester,
                                     'ref': self.clearance_no,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'validate'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search(
                    [('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        else:
            raise Warning(_("An issue was faced when validating!"))

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

        self.move_id.post()
        if self.move2_id:
            self.move2_id.post()

    def set_to_draft(self):
        self.state = 'draft'
        self.mn_app_id = None
        self.au_app_id = None
        self.fm_app_id = None
        self.at_app_id = None

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def cancel_button(self):
        self.move_id.button_cancel()
        if self.move2_id:
            self.move2_id.button_cancel()
        self.state = 'fm_app'


################################################
# Custody clearance line model
class custody_clearance_line(models.Model):
    _name = 'custody.clearance.line'
    _description = 'Custody clearance details.'

    custody_clearance_id = fields.Many2one('custody.clearance', string='Custody Clearance', ondelete="cascade")
    name = fields.Char('Narration', required=True)
    amount = fields.Float('Amount', required=True)
    notes = fields.Char('Notes')
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account/Cost Center')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
