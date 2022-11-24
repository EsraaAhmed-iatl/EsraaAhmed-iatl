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


class ProductCategory(models.Model):
    _inherit = 'product.category'

    compute_cost = fields.Boolean('Compute Standard Cost?')
    sl_markup = fields.Float("Sales Mark Up", digits=(6, 2), default=0)

    def update_price(self):
        for product in self.env['product.template'].search([('categ_id', '=', self.id)]):
            if self.compute_cost == True:
                standard_price = product.cp_euro + (product.cp_euro * self.env.company.cp_markup / 100)
                list_price = standard_price + (standard_price * self.sl_markup / 100)
                product.write({'standard_price': standard_price, 'list_price': list_price})
            elif product.standard_price:
                list_price = product.standard_price + (product.standard_price * self.sl_markup / 100)
                product.write({'list_price': list_price})


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    compute_cost = fields.Boolean('Compute Standard Cost?', related='categ_id.compute_cost')
    cp_euro = fields.Float('Cost Price (Supplier Cost)')

    @api.onchange('cp_euro', 'compute_cost')
    def _onchange_eur_standard_cost(self):
        if self.compute_cost == True:
            if self.cp_euro or self.env.company.cp_markup:
                self.standard_price = self.cp_euro + (self.cp_euro * self.env.company.cp_markup / 100)
                self.sale_price(self.standard_price)

    @api.onchange('standard_price', 'categ_id.sl_markup')
    def _onchange_list_price(self):
        if self.standard_price and self.categ_id.sl_markup:
            self.list_price = self.standard_price + (self.standard_price * self.categ_id.sl_markup / 100)

    def sale_price(self, standard_price):
        if standard_price:
            self.list_price = standard_price + (standard_price * self.categ_id.sl_markup / 100)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('cp_euro', 'compute_cost')
    def _onchange_eur_standard_cost(self):
        if self.compute_cost == True:
            if self.cp_euro or self.env.company.cp_markup:
                self.standard_price = self.cp_euro + (self.cp_euro * self.env.company.cp_markup / 100)
                self.sale_price(self.standard_price)

    @api.onchange('standard_price', 'categ_id.sl_markup')
    def _onchange_list_price(self):
        if self.standard_price and self.categ_id.sl_markup:
            self.list_price = self.standard_price + (self.standard_price * self.categ_id.sl_markup / 100)

    def sale_price(self, standard_price):
        if standard_price:
            self.list_price = standard_price + (standard_price * self.categ_id.sl_markup / 100)
