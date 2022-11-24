# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import AccessError, UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        if vals.get('customer_code', _('New')) == _('New'):
            vals['customer_code'] = self.env['ir.sequence'].next_by_code('customer.code') or _('New')
        result = super(ResPartner, self).create(vals)
        return result

    customer_code = fields.Char(string='Customer Code', required=True, copy=False, readonly=True,
                           index=True, default=lambda self: _('New'))

    _sql_constraints = [
        ('customer_code_company_uniq', 'Check(1=1)', 'The code of the account must be unique per company !')
    ]

    # @api.model
    # def create(self, vals_list):
    #     res = super(ResPartner, self).create(vals_list)
    #     if self.customer_code:
    #         result = self.env['res.partner'].search([('customer_code', '=', vals_list['customer_code'])
    #                                                     ,('id', '!=', res.id)])
    #         if result:
    #             raise ValidationError(_("The code of the account must be  unique per company !"))
    #     return res
    #
    # def write(self, vals):
    #     res = super(ResPartner, self).write(vals)
    #     if self.customer_code:
    #         result = self.env['res.partner'].search([('customer_code', '=', self.customer_code),
    #                                                  ('id', '!=', self.id)])
    #         if result:
    #             raise ValidationError(_("The code of the account must be write  unique per company !"))
    #     return res

    # overriding Search
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('customer_code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()
