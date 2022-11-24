#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Costing                                                    #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################


from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import Warning, ValidationError, _logger, UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    cp_markup = fields.Float("Cost Price Mark Up", digits=(6, 2), default=0)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cp_markup = fields.Float("Cost Markup", related='company_id.cp_markup', readonly=False)

    def update_cost(self):
        for product in self.env['product.template'].search([]):
            if product.compute_cost == True:
                standard_price = product.cp_euro + (product.cp_euro * self.cp_markup / 100)
                list_price = standard_price + (standard_price * product.categ_id.sl_markup / 100)
                product.write({'standard_price': standard_price, 'list_price': list_price})
