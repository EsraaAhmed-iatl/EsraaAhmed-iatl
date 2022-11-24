# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_done = fields.Boolean('Delivery done', compute='_check_delivery_state', default=False, copy=False)
    return_qty = fields.Boolean(string="Return Qty", compute='_check_return_qty', default=False, copy=False)
    sale_count = fields.Integer(string='Picking', compute='_compute_sale_count', default=False, copy=False)
    sale_return_ids = fields.One2many("order.return", "sale_id", string="Sale Return", required=False, )

    def _compute_sale_count(self):
        for rec in self:
            rec.sale_count = rec.env['order.return'].search_count([('sale_id', '=', rec.id)])

    def action_open_order_return(self):
        return {
            'name': 'Return',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'order.return',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id, 'default_return_type': 'sale'},
            'target': 'current'
        }

    def _check_return_qty(self):
        self.return_qty = False
        for line in self.order_line:
            if line.product_uom_qty == line.qty_return:
                self.return_qty = True

    def _check_delivery_state(self):
        self.delivery_done = False
        if self.picking_ids:
            for rec in self.picking_ids:
                if rec[0].state == 'done':
                    self.delivery_done = True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_return = fields.Float("Return Qty", digits='Product Unit of Measure', required=False, readonly=False,
                              default=False, copy=False)
