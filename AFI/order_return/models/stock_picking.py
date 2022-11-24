# -*- coding: utf-8 -*-

from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    return_id = fields.Many2one('order.return')

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.move_ids_without_package:
            if self.return_id:
                self.return_id.write({'state': 'done'})
        return res
