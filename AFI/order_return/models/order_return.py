# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round


class OrderReturn(models.Model):
    _name = 'order.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _description = 'Order Return'

    name = fields.Char(string="Return Reference", required=True, index=True, default='New', readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", required=False, readonly=True)
    return_date = fields.Date(string="Return Date", required=False, default=fields.Date.context_today)
    reason_id = fields.Text(string="Return Reason", required=False, )
    return_type = fields.Selection(selection=[('purchase', 'Purchase'),
                                              ('sale', 'Sale'), ],
                                   string="Return Type", required=False, )
    origin = fields.Char(string="Source Document", required=False, )
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirmed'),
                                        ('done', 'Done'),
                                        ('approve', 'Approved'),
                                        ('cancel', 'Cancel')
                                        ], string="Status", required=False, default='draft', tracking=True, )
    return_line = fields.One2many("order.return.line", "return_id", string="Order Return Line", required=False, )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    location_id = fields.Many2one('stock.location', string="Return Location", tracking=True, )
    picking_id = fields.Many2one('stock.picking', string="Return Picking", tracking=True, store=True)
    picking_count = fields.Integer(string='Picking', compute='_compute_picking_count')
    move_count = fields.Integer(string='Returned BILL/Invoice', compute='_compute_reverse_move_count')
    amount_total = fields.Float(string="Total", required=False, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=5)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')

    bill_ids = fields.Many2many('account.move', string="Bill")

    @api.depends('return_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.return_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    # @api.depends('return_line', 'return_line.price_subtotal')
    # def _compute_amount_total(self):
    #     total_amount =0
    #     for line in self.return_line:
    #         total_amount += line.price_subtotal
    #     self.amount_total = total_amount

    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = rec.env['stock.picking'].search_count([('return_id', '=', rec.id)])

    def _compute_reverse_move_count(self):
        for rec in self:
            rec.move_count = rec.env['account.move'].search_count([('return_order_id', '=', rec.id)])

    def action_open_picking(self):
        return {
            'name': 'Picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('return_id', '=', self.id)],
            'target': 'current',
        }

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        return_line = [(5,)]
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        line_fields = [f for f in self.env['order.return.line']._fields.keys()]
        return_line_data_tmpl = self.env['order.return.line'].default_get(line_fields)
        for move in self.picking_id.move_lines:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            return_line_data = dict(return_line_data_tmpl)
            return_line_data.update(self._prepare_order_return_picking_line_vals_from_move(move))
            return_line.append((0, 0, return_line_data))
        if self.picking_id and not return_line:
            raise UserError(
                _("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.return_line = return_line
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id
        for line in self.mapped('return_line'):
            line.onchange_product_id()

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
            'name': stock_move.product_id.name,
            'qty_return': quantity,
            # 'delivery_qty': quantity,
            'move_id': stock_move.id,
            'product_uom': stock_move.product_id.uom_id.id,
        }

    def action_confirm_return(self):
        self.write({'state': 'confirm'})

    def action_cancel_return(self):
        self.write({'state': 'cancel'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = {
            'product_id': return_line.product_id.id,
            'product_uom_qty': return_line.qty_return,
            'product_uom': return_line.product_id.uom_id.id,
            'picking_id': new_picking.id,
            'state': 'draft',
            'to_refund': return_line.to_refund,
            'date': fields.Datetime.now(),
            'location_id': return_line.move_id.location_dest_id.id,
            'location_dest_id': self.location_id.id or return_line.move_id.location_id.id,
            'picking_type_id': new_picking.picking_type_id.id,
            'warehouse_id': self.picking_id.picking_type_id.warehouse_id.id,
            'origin_returned_move_id': return_line.move_id.id,
            'procure_method': 'make_to_stock',
        }
        return vals

    def _create_returns(self):
        for return_move in self.return_line.mapped('move_id'):
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

            # create new picking for returned products
        picking_type_id = self.picking_id.picking_type_id.return_picking_type_id.id or self.picking_id.picking_type_id.id
        new_picking = self.picking_id.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'state': 'draft',
            'origin': _("Return of %s", self.picking_id.name),
            'location_id': self.picking_id.location_dest_id.id,
            'return_id': self.id,
            'location_dest_id': self.location_id.id})
        new_picking.message_post_with_view('mail.message_origin_link',
                                           values={'self': new_picking, 'origin': self.picking_id},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        returned_lines = 0
        for return_line in self.return_line:
            if not return_line.move_id:
                raise UserError(_("You have manually created product lines, please delete them to proceed."))
            if return_line.qty_return:
                returned_lines += 1
                vals = self._prepare_move_default_values(return_line, new_picking)
                r = return_line.move_id.copy(vals)
                vals = {}
                move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                # link to original move
                move_orig_to_link |= return_line.move_id
                # link to siblings of original move, if any
                move_orig_to_link |= return_line.move_id \
                    .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel')) \
                    .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))
                move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                # link to children of originally returned moves, if any. Note that the use of
                # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
                # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
                # return directly to the destination moves of its parents. However, the return of
                # the return will be linked to the destination moves.
                move_dest_to_link |= return_line.move_id.move_orig_ids.mapped('returned_move_ids') \
                    .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel')) \
                    .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))
                vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link]
                vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                r.write(vals)
        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking.id, picking_type_id

    def action_approve_return(self):
        for rec in self:
            new_picking_id, pick_type_id = rec._create_returns()
        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_planning_issues': False,
            'search_default_available': False,
        })
        self.write({'state': 'approve'})
        # return {
        #     'name': _('Returned Picking'),
        #     'view_mode': 'form,tree,calendar',
        #     'res_model': 'stock.picking',
        #     'res_id': new_picking_id,
        #     'type': 'ir.actions.act_window',
        #     'context': ctx,
        # }

    def action_open_return_moves(self):
        return {
            'name': 'Return',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('return_order_id', '=', self.id)],
            'target': 'current'
        }


class OrderReturnLine(models.Model):
    _name = 'order.return.line'
    _description = 'Order Return Line'

    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, )
    return_id = fields.Many2one('order.return', string='Return Order', index=True,
                                ondelete='cascade')
    state = fields.Selection(related='return_id.state', store=True, )
    delivery_qty = fields.Float(string="Delivery Qty", required=False, )
    qty_return = fields.Float("Return Qty", digits='Product Unit of Measure', required=False,
                              default=False, copy=False)
    partner_id = fields.Many2one('res.partner', related='return_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    return_date = fields.Date(related='return_id.return_date', string="Return Date", required=False, )
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=False)
    price_unit = fields.Monetary('Unit Price', required=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)

    currency_id = fields.Many2one("res.currency", related='return_id.currency_id', string="Currency", readonly=True,
                                  required=True)
    move_id = fields.Many2one("stock.move", string="Move", required=False, )
    to_refund = fields.Boolean(string="Update quantities on SO/PO", default=True,
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain=['|', ('active', '=', False), ('active', '=', True)])

    @api.depends('qty_return', 'product_id', 'price_unit', 'currency_id', 'tax_ids')
    def _compute_amount(self):
        """
                Compute the amounts of the SRO line.
                """
        for line in self:
            price = line.price_unit
            taxes = line.tax_ids.compute_all(price, line.return_id.currency_id, line.qty_return,
                                             product=line.product_id, partner=line.return_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_ids.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        if self.product_id:
            self.price_unit = self.product_id.standard_price
        return result
