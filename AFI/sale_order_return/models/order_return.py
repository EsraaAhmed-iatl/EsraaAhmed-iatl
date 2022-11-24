# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning,UserError



class OrderReturn(models.Model):
    _inherit = 'order.return'

    sale_id = fields.Many2one("sale.order", string="Sale", required=False, )
    sale_picking_id = fields.Many2one("stock.picking", string="Return Picking", required=False, )
    invoice_status = fields.Selection(related='sale_id.invoice_status', required=False, )

    @api.onchange('sale_picking_id')
    def _onchange_sale_picking_id(self):
        self.picking_id = self.sale_picking_id.id

    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        for rec in self:
            rec.origin = rec.sale_id.name
            rec.partner_id = rec.sale_id.partner_id.id

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.sale_id.client_order_ref or '',
            'move_type': 'out_refund',
            'narration': self.sale_id.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.sale_id.campaign_id.id,
            'medium_id': self.sale_id.medium_id.id,
            'source_id': self.sale_id.source_id.id,
            'invoice_user_id': self.sale_id.user_id and self.sale_id.user_id.id,
            'team_id': self.sale_id.team_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.sale_id.partner_shipping_id.id,
            'fiscal_position_id': (
                    self.sale_id.fiscal_position_id or self.sale_id.fiscal_position_id.get_fiscal_position(
                self.sale_id.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.sale_id.payment_term_id.id,
            'payment_reference': _('Reversal of: %(name)s, %(reason)s', name=self.name, reason=self.reason_id),
            'transaction_ids': [(6, 0, self.sale_id.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'return_order_id': self.id,
            # 'sale_id': self.sale_id.id,
        }
        return invoice_vals

    def action_reverse(self):

        invoice_line_vals = []
        invoice_vals_list = []
        invoice_vals = self._prepare_invoice()
        for line in self.return_line:
            if line.sale_order_id.invoice_lines and line.sale_order_id.invoice_lines != 'draft':
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line()), )
        invoice_vals['invoice_line_ids'] = invoice_line_vals
        invoice_vals_list.append(invoice_vals)
        invoice_reverse = self.env['account.move'].create(invoice_vals_list)
        for move in invoice_reverse:
            move.message_post_with_view('mail.message_origin_link',
                                        values={'self': move,
                                                'origin': self},
                                        subtype_id=self.env.ref('mail.mt_note').id
                                        )
            # self.bill_ids = invoice_reverse.id

            # self.env['account.move.line'].create({invoice_line_vals})
            # invoice_line_reverse = self.env['account.move.line'].create(invoice_line_vals)

        # new_moves = []
        # new_invoice_line_ids = []
        # for move in self.bill_ids:
        #     default_values_list = [
        #         {'ref': _('Reversal of: %(move_name)s, %(reason)s', move_name=move.name, reason=self.reason_id),
        #          'date': fields.Date.context_today(self),
        #          'return_order_id': self.id,
        #          'sale_id':self.sale_id.id,
        #          }]
        #     new_move = move._reverse_moves(default_values_list, cancel=False)
        #     new_moves.append(new_move.id)
        #
        # return action

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            if vals['return_type'] == 'sale':
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.return') or _('New')
        return super(OrderReturn, self).create(vals)


class OrderReturnLine(models.Model):
    _inherit = 'order.return.line'

    sale_order_id = fields.Many2one('sale.order.line', string='sale Order', )

    def _prepare_invoice_line(self):
        move_line_vals = {
            'display_type': self.sale_order_id.display_type,
            'sequence': self.sale_order_id.sequence,
            'product_id': self.product_id.id,
            'name': self.name,
            'quantity': self.qty_return,
            'price_unit': self.price_unit,
            'analytic_account_id': self.sale_order_id.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.sale_order_id.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.sale_order_id.id)],
            'account_id': self.product_id.categ_id.return_sale_account.id,
            'tax_ids': [(6, 0, self.tax_ids.ids)],

        }
        return move_line_vals
