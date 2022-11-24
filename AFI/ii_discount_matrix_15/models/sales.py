# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

import babel
from datetime import date
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approve = fields.Boolean(string='approve', compute='_check_approve_authorty')
    show_approve = fields.Boolean(string='approve', compute='_show_approve')
    approve_position = fields.Many2one('hr.job', string='Approve Position', compute='get_allowed_discount_person')
    total_discount = fields.Float('Total Discount', compute='_get_total_dis')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('approve_sale', 'Quotation Approve'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    def action_approve(self):
        self.state = 'approve_sale'
                
    def set_to_draft(self):
    	for order in self:
    		if order.state == 'approve_sale':
    			order.state = 'draft'

    # @api.depends('order_line.discount', 'order_line')
    # def _get_total_dis(self):
    #     count = 0
    #     for rec in self:
    #         total = 0.0
    #         rec.total_discount = 0.0
    #         for line in rec.order_line:
    #             count += 1
    #             total += line.discount
    #         rec.total_discount = count and total / count or total

    @api.depends('ks_global_discount_type', 'ks_global_discount_rate', 'order_line', 'order_line.price_subtotal')
    def _get_total_dis(self):
        for rec in self:
            so_total = 0
            for line in rec.order_line:
                so_total += line.price_subtotal
            total = so_total
            if rec.ks_global_discount_rate == 0.0:
                rec.total_discount = 0.0
            else:
                if rec.ks_global_discount_type == 'percent':
                    rec.total_discount = rec.ks_global_discount_rate
                else:
                    rec.total_discount = rec.ks_global_discount_rate / total * 100

    @api.depends('user_id', 'total_discount', 'order_line')
    def get_allowed_discount_person(self):
        for rec in self:
            rec.approve_position = False
            if rec.total_discount == 0.0:
                employee = self.env['hr.employee'].sudo().search([('user_id', '=', rec.user_id.id)], limit=1)
                employee_position = employee.sudo().job_id.id
                rec.approve_position = employee_position
            else:
                today = date.today()
                level_check = self.env['discount.matrix.line'].search([
                    ('matrix_id.date_from', '<=', today),('matrix_id.date_to', '>=', today),
                    ('min_allowed', '<=', rec.total_discount),('max_allowed', '>=',rec.total_discount)], limit=1)
                if level_check:
                    rec.approve_position = level_check.position_id.id

    @api.depends('user_id')
    def _check_approve_authorty(self):
        for obj in self:
            users = []
            obj.approve = False
            if obj.approve_position:
                employee = self.env['hr.employee'].sudo().search([('user_id', '=', obj.user_id.id)], limit=1)
                employee_position = employee.sudo().job_id.id
                filter = self.env['hr.employee'].sudo().search([('job_id', '=', obj.approve_position.id)])
                for emp in filter:
                    if emp.user_id.id not in users:
                        users.append(emp.user_id.id)

                if obj.approve_position == employee_position:
                    obj.approve = True
                else:
                    if self.env.user.id in users:
                        obj.approve = True

    def _show_approve(self):
        for rec in self:
            rec.show_approve = False
            if rec.state in ['draft', 'sent'] and rec.approve == True:
                rec.show_approve = True
