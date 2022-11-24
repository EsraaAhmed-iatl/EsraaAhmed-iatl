# -*- coding: utf-8 -*-

from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.move_ids_without_package:
            if self.return_id:
                self.return_id.write({'state': 'done'})
                for r in self.move_ids_without_package:
                    r.sale_line_id.write({'qty_return': r.quantity_done, })
        return res
