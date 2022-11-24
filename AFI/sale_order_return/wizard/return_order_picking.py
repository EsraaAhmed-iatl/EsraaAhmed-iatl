# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OrderReturnLine(models.TransientModel):
    _inherit = 'order.return.picking.line'

    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line', index=True)


class OrderReturnPicking(models.TransientModel):
    _inherit = 'order.return.picking'

    @api.model
    def default_get(self, fields):
        rec = super(OrderReturnPicking, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'sale.order':
            active_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
            rec.update({'is_sale': True,
                        'sale_id': active_id.id})
        return rec

    sale_id = fields.Many2one("sale.order", string="Sale", required=False, )
    sale_picking_id = fields.Many2one("stock.picking", string="Picking", required=False, )
    is_sale = fields.Boolean(string="Is Sale", )
    invoice_ids = fields.Many2many("account.move", string="Invoicing")

    @api.onchange('sale_picking_id')
    def _onchange_sale_picking_id(self):
        self.picking_id = self.sale_picking_id.id

    def _prepare_order_return_vals(self):
        values = super(OrderReturnPicking, self)._prepare_order_return_vals()
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'sale.order':
            active_id = self.env['sale.order'].browse(self.env.context.get('active_id'))

            values.update({'sale_id': active_id.id,
                           'sale_picking_id': self.sale_picking_id.id,
                           'partner_id': active_id.partner_id.id,
                           'origin': active_id.name,
                           'return_type': 'sale',
                           })
        return values

    def create_order_returns(self):
        values = self._prepare_order_return_vals()
        order_return = self.env['order.return'].create(values)
        for line in self.product_return_moves:
            self.env['order.return.line'].create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'qty_return': line.quantity,
                'return_id': order_return.id,
                'move_id': line.move_id.id,
                'to_refund': line.to_refund,
                'price_unit': line.sale_line_id.price_unit,
                'sale_order_id': line.sale_line_id.id,
                'tax_ids': [(6, 0, line.sale_line_id.tax_id.ids)],
            })
            # order_return_line.onchange_product_id()

    @api.model
    def _prepare_order_return_picking_line_vals_from_move(self, stock_move):
        rec = super(OrderReturnPicking, self)._prepare_order_return_picking_line_vals_from_move(stock_move=stock_move)

        rec.update({'sale_line_id': stock_move.sale_line_id.id})

        return rec
