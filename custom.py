##############################################################################
#    Description: Sale Customization                                   #
#    Author: IntelliSoft Software                                            #
#    Date: May 2020 -  Till Now                                              #
##############################################################################

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
from odoo.exceptions import UserError, AccessError, Warning ,ValidationError
import pytz
from psycopg2 import sql, extras
from odoo import api, exceptions, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
import math
import babel
import time
from odoo import tools

_logger = logging.getLogger(__name__)
# class ReturnPicking(models.TransientModel):
#     _inherit = "stock.return.picking"
#
#     @api.model
#     def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
#         print('llllllllll',stock_move)
#         quantity = stock_move.product_qty
#         for move in stock_move.move_dest_ids:
#             if move.origin_returned_move_id and move.origin_returned_move_id != stock_move:
#                 continue
#             if move.state in ('partially_available', 'assigned'):
#                 quantity -= sum(move.move_line_ids.mapped('product_qty'))
#             elif move.state in ('done'):
#                 quantity -= move.product_qty
#                 lot = move.move_line_ids_without_package.lot_id
#                 print('llllooot',lot.move.move_line_ids_without_package)
#         quantity = float_round(quantity, precision_rounding=stock_move.product_uom.rounding)
#         return {
#             'product_id': stock_move.product_id.id,
#             'quantity': quantity,
#             'move_id': stock_move.id,
#             'uom_id': stock_move.product_id.uom_id.id,
#         }

class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    lot_id = fields.Many2one('stock.production.lot')


# class MailNotification(models.Model):
#     _inherit = 'mail.notification'
#
#     @api.model
#     def mark_as_read(self):
#         for rec in self.env['mail.notification'].search([]):
#             # message = rec.mail_message_id
#             # if message.model == 'finance.approval' or message.model == 'hr.leave.allocation':
#             rec.is_read = True


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    coordinator_account = fields.Many2one('res.users', 'Account Coordinator')
    head_account = fields.Many2one('res.users', 'Head of Account')
    account_managers = fields.Many2many('res.users', 'team_user_rel', 'team_id', 'user_id', 'Account Managers')
    member_ids = fields.Many2many('res.users', 'team_users_rel', 'sale_team_id', 'user_id', string='Channel Members')
    auto_invoice = fields.Boolean('Auto Invoice', default=True)


class ProductSpecialPriceList(models.Model):
    _name = 'product.price.list.special'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('res.partner', 'Partner')
    line_ids = fields.One2many('product.price.list.line', 'line_id', 'Lines')


class ProductSpecialPriceListLine(models.Model):
    _name = 'product.price.list.line'
    # _rec_name = 'genset_id'

    line_id = fields.Many2one('product.price.list.special', 'Partner')
    product_id = fields.Many2one('product.product', 'Product')
    currency_id = fields.Many2one('res.currency', 'Currency')
    currency_price = fields.Float('Price')


class ProductGenset(models.Model):
    _name = 'product.genset'
    _rec_name = 'genset_id'

    genset_id = fields.Many2one('product.product', 'Product')
    currency_id = fields.Many2one('res.currency', 'Currency')
    currency_price = fields.Float('Price')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    genset_ids = fields.One2many('product.genset', 'genset_id', 'Genset')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    customer_name = fields.Char('Customer Name')
    team_id = fields.Many2one('crm.team', 'Account', compute='_compute_team', store=True)

    @api.depends('sale_id')
    def _compute_team(self):
        for rec in self:
            rec.team_id = False
            if rec.sale_id:
                rec.team_id = rec.sale_id.team_id.id
            # for line in rec.move_ids_without_package:
            #     analytic = line.sale_line_id.order_id.team_id.id
            #     rec.team_id = analytic


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).reverse_moves()
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        if self.refund_method == 'refund':
            refund = 'partial_refund'
        else:
            refund = 'full'
        moves.update({
            'refund_method': refund,
        })
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_name = fields.Char('Customer Name')
    refund_method = fields.Selection([
        ('full', 'Fully Refund'),
        ('partial_refund', 'Partial Refund'),
    ], string='Refund Method')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_type = fields.Selection([('sale', 'Sales Order'), ('direct_sale', 'Direct Sales')], default='sale')
    customer_name = fields.Char('Customer Name')
    refund_method = fields.Selection([
        ('full', 'Fully Refund'),
        ('partial_refund', 'Partial Refund'),
    ], string='Invoice Refund Status', compute='_get_refund_status')
    approve_date = fields.Date('Approve Date')
    confirm_date = fields.Date('Confirmation Date')
    delivery_from_stock_date = fields.Date('Delivery Date')
    order_name_str = fields.Char('Order Ref', compute='_get_order_name_str')

    @api.depends('name')
    def _get_order_name_str(self):
        for rec in self:
            if rec.name:
                rec.order_name_str = rec.name

    @api.depends('invoice_ids.refund_method')
    def _get_refund_status(self):
        for order in self:
            pickings = order.invoice_ids
            if pickings:
                for pic in pickings:
                    refund_method = pic.refund_method
                    order.refund_method = refund_method
            else:
                order.refund_method = False

    # prepare invoice
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'customer_name': self.customer_name,
            'invoice_date': date.today(),
        })
        return res

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.confirm_date = date.today()
        so_model = self.env['ir.model'].sudo().search([('model', 'like', 'sale.order')], limit=1)
        self.env['mail.activity'].search(
            [('user_id', '=', self.env.uid), ('res_id', '=', self.id), ('res_model_id', '=', so_model.id)]).action_done()
        return res

    def action_approve(self):
        for rec in self.order_line:
            if rec.product_id.type == 'product' and rec.available == False and rec.blocked == True and rec.blocked_gm == False:
                raise UserError(_('Quantity Item ordered blocked(%s) Place Check Approved Gm.') % (
                rec.product_id.name))
        if self.sale_type == 'sale':
            self.state = 'approve_sale'
            self.approve_date = date.today()
            fm_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Sale Order Confirmation')], limit=1).id
            self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (fm_group_id))
            for fm in list(filter(lambda x: (
                    self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                                  self.env.cr.fetchall())):
                vals = {
                    'activity_type_id': self.env['mail.activity.type'].sudo().search(
                        [('name', 'like', 'Sale Order')],
                        limit=1).id,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'sale.order')],
                                                                       limit=1).id,
                    'user_id': fm[0] or 1,
                    'summary': self.name,
                }
                # add lines
                self.env['mail.activity'].sudo().create(vals)
        else:
            # self.sale_type = 'direct_sale'
            self.approve_date = date.today()
            self.action_confirm()
            for do_pick in self.picking_ids:
                do_pick.write({'customer_name': self.customer_name})


class SamasuResPartner(models.Model):
    _inherit = 'res.partner'

    customer_vat = fields.Boolean('VAT?')
    direct = fields.Boolean('Direct Sales?')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Cost Center')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    forecast_in = fields.Float('Forecast In', compute="_get_forecast_qty", store=True)
    forecast_out = fields.Float('Forecast Out', compute="_get_forecast_qty", store=True)
    qty_balance = fields.Float('Balance', compute="_get_forecast_qty", store=True)
    team_id = fields.Many2one('crm.team', 'Account', related='order_id.team_id', store=True)

    # @api.onchange('price_unit', 'prices')
    # def onchange_unit_price(self):
    #     raise UserError(_('You are not allowed to change Prices'))

    @api.onchange('product_id')
    def onchange_lot_id(self):
        domain = []
        products = self.env['unit.details'].search([('product_id', '=', self.product_id.id)])
        for product in products:
            domain.append(product.unit_id.id)

        return {'domain': {'product_uom': [('id', 'in', domain)]}}

    @api.depends('product_id')
    def _get_forecast_qty(self):
        for rec in self:
            rec.forecast_in = rec.product_id.incoming_qty
            rec.forecast_out = rec.product_id.outgoing_qty
            rec.qty_balance = rec.product_id.free_qty


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    team_id = fields.Many2one('crm.team', 'Account', related='product_id.team_id', store=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    team_id = fields.Many2one('crm.team', 'Account', related='product_id.team_id', store=True)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    team_id = fields.Many2one('crm.team', 'Account', related='product_id.team_id', store=True)
