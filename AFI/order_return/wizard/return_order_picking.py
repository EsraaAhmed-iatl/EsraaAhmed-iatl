# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round


class OrderReturnLine(models.TransientModel):
    _name = "order.return.picking.line"
    _rec_name = 'product_id'
    _description = 'Order Return Picking Line'

    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', '=', product_id)]")
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='move_id.product_uom', readonly=False)
    wizard_id = fields.Many2one('order.return.picking', string="Wizard")
    move_id = fields.Many2one('stock.move', "Move")
    to_refund = fields.Boolean(string="Update quantities on SO/PO", default=True,
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')


class OrderReturnPicking(models.TransientModel):
    _name = 'order.return.picking'
    _description = 'Order Return Picking'

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError(_("You may only return one picking at a time."))
        res = super(OrderReturnPicking, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.picking':
            picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
            if picking.exists():
                res.update({'picking_id': picking.id})
        return res

    picking_id = fields.Many2one('stock.picking')
    product_return_moves = fields.One2many('order.return.picking.line', 'wizard_id', 'Moves')
    move_dest_exists = fields.Boolean('Chained Move Exists', readonly=True)
    original_location_id = fields.Many2one('stock.location')
    parent_location_id = fields.Many2one('stock.location')
    company_id = fields.Many2one(related='picking_id.company_id')
    location_id = fields.Many2one(
        'stock.location', 'Return Location',
        domain="['|', ('id', '=', original_location_id), '|', '&', ('return_location', '=', True), ('company_id', '=', False), '&', ('return_location', '=', True), ('company_id', '=', company_id)]")
    return_date = fields.Date(string="Return Date", required=False, default=fields.Date.context_today)
    reason_id = fields.Text(string="Return Reason", required=False, )

    #
    # @api.onchange('picking_id')
    # def _onchange_bill_ids(self):
    #     bill_ids = self.env['purchase.order'].search([('id', '=', self._context.get('active_id'))]).mapped(
    #         'invoice_ids')
    #     if bill_ids:
    #         return {'domain': {'bill_ids': [('id', 'in', bill_ids.ids)]}}

    def _prepare_order_return_vals(self):
        values = {'return_date': self.return_date,
                  'location_id': self.location_id.id,
                  'picking_id': self.picking_id.id,
                  'reason_id': self.reason_id,
                  # 'bill_ids': self.bill_ids.ids,
                  }
        return values

    def create_order_returns(self):
        values = self._prepare_order_return_vals()
        order_return = self.env['order.return'].create(values)
        for line in self.product_return_moves:
            order_return_line = self.env['order.return.line'].create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'qty_return': line.quantity,
                'return_id': order_return.id,
                'move_id': line.move_id.id,
                'to_refund': line.to_refund,
            })
            order_return_line.onchange_product_id()

        # return values

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['order.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['order.return.picking.line'].default_get(line_fields)
        for move in self.picking_id.move_lines:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            if move.move_dest_ids:
                move_dest_exists = True
            product_return_moves_data = dict(product_return_moves_data_tmpl)
            product_return_moves_data.update(self._prepare_order_return_picking_line_vals_from_move(move))
            product_return_moves.append((0, 0, product_return_moves_data))
        if self.picking_id and not product_return_moves:
            raise UserError(
                _("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id

    @api.model
    def _prepare_order_return_picking_line_vals_from_move(self, stock_move):
        quantity = stock_move.product_qty
        for move in stock_move.move_dest_ids:
            if move.origin_returned_move_id and move.origin_returned_move_id != stock_move:
                continue
            if move.state in ('partially_available', 'assigned'):
                quantity -= sum(move.move_line_ids.mapped('product_qty'))
            elif move.state in ('done'):
                quantity -= move.product_qty
        quantity = float_round(quantity, precision_rounding=stock_move.product_uom.rounding)
        return {
            'product_id': stock_move.product_id.id,
            'quantity': quantity,
            'move_id': stock_move.id,
            'uom_id': stock_move.product_id.uom_id.id,
        }

        # else:
        #     raise ValidationError(_('this PO has no bills.'))
