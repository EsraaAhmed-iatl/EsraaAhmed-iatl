# -*- coding: utf-8 -*-

from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    return_order_id = fields.Many2one('order.return', copy=False)
