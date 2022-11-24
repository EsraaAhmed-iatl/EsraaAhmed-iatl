# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL International Pvt. Ltd.
#    Copyright (C) 2020-TODAY Tech-Receptives(<http://www.iatl-sd.com>).
#
###############################################################################

from odoo import fields, models, api


class ProductCategory(models.Model):
    _inherit = "product.category"

    return_sale_account = fields.Many2one('account.account', string="Return on sale account ")
