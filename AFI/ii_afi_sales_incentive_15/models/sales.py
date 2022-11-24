# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

import babel
from datetime import date
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_line_ids = fields.One2many(comodel_name="commission.payment.lines",
                                          inverse_name="sales_id", string="", required=False, )

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.get_commission()
        return res

    def get_commission(self):
        for rec in self:
            library_management_lines = [(5, 0, 0)]
            positions = self.env['sale.incentive.line'].search([])
            for line_id in positions:
                if line_id.level1_check:
                    emp = self.env['hr.employee'].search([('user_id', '=', rec.user_id.id)])
                    line = (0, 0, {
                        'employee_id': emp.id,
                        'position_id': line_id.position_id.id,
                        'amount': rec.amount_total * line_id.commission / 100,
                        'commission': line_id.commission,
                        'level1_check': line_id.level1_check,
                        'level2_check': line_id.level2_check,
                    })
                    library_management_lines.append(line)

                    if library_management_lines:
                        rec.commission_line_ids = library_management_lines

                if line_id.level2_check:
                    emp = self.env['hr.employee'].search([('user_id', '=', rec.team_id.user_id.id)])

                    line = (0, 0, {
                        'employee_id': emp.id,
                        'position_id': line_id.position_id.id,
                        'amount': rec.amount_total * line_id.commission / 100,
                        'commission': line_id.commission,
                        'level1_check': line_id.level1_check,
                        'level2_check': line_id.level2_check,
                    })

                    library_management_lines.append(line)

                    if library_management_lines:
                        rec.commission_line_ids = library_management_lines



                else:
                    emp = self.env['hr.employee'].search([('job_id', '=', line_id.position_id.id)])

                    line = (0, 0, {
                        'employee_id': emp.id,
                        'position_id': line_id.position_id.id,
                        'amount': rec.amount_total * line_id.commission / 100,
                        'commission': line_id.commission,
                        'level1_check': line_id.level1_check,
                        'level2_check': line_id.level2_check,
                    })

                    library_management_lines.append(line)

                    if library_management_lines:
                        rec.commission_line_ids = library_management_lines


class CommissionPayment(models.Model):
    _name = 'commission.payment.lines'

    def action_create_payment(self):
        for rec in self:
            if rec.amount > 0.0:
                res = self.env['finance.approval'].create({
                    'fa_date': rec.sales_id.date_order,
                    'request_amount': rec.amount,
                    'reason': '''Sale's commission for : ''' + str(rec.employee_id.name),
                    'commission_id': rec.sales_id.id,
                    'request_currency': rec.sales_id.currency_id.id,
                })
                if res:
                    rec.state = 'post'
            else:
                raise ValidationError(_("The amount must be greater than 0"))

    position_id = fields.Many2one('hr.job', 'Position', required=True)
    amount = fields.Float(string="Amount", required=True)
    commission = fields.Float(string="Commission (%)", required=True)
    state = fields.Selection(string="State",
                             selection=[('draft', 'Draft'),
                                        ('post', 'Posted'),
                                        ],
                             readonly=True,
                             required=False, default='draft')
    level1_check = fields.Boolean(string="", )
    level2_check = fields.Boolean(string="", )
    sales_id = fields.Many2one(comodel_name="sale.order", string="Sale Order", required=False, )

    partner_id = fields.Many2one(comodel_name="res.partner",
                                 track_visibility='onchange',
                                 string="Partner", required=False, )
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False, )


class FinanceApproval(models.Model):
    _inherit = 'finance.approval'

    commission_id = fields.Many2one(comodel_name="sale.order", string="", required=False, )
