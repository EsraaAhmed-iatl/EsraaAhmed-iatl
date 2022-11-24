from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SoConfigurationApprove(models.Model):
    _name = "so.config.approve"

    job_position_id = fields.Many2one(comodel_name="hr.job", string="Job Position", required=True, )
    limit = fields.Float(string="Limit", required=False, )
    is_check = fields.Boolean(string="Check")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('amount_total')
    def get_position(self):
        for rec in self:
            employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
            rec.position_id = employee_rec.job_id.id
            job = self.env['so.config.approve'].search([
                ('job_position_id', '=', rec.position_id.id),
                ('limit', '>=', rec.amount_total),
            ])
            if job:
                rec.is_check = True
            else:
                rec.is_check = False

    position_id = fields.Many2one(comodel_name="hr.job", string="Position",
                                  required=False,
                                  compute='get_position',
                                  store=True
                                  )
    is_check = fields.Boolean(string="Check",
                              compute='get_position',
                              )
    is_immediate = fields.Boolean(string="Immediate", related='payment_term_id.is_immediate')

    is_delivery_approve = fields.Boolean(string="Delivery Approve", copy=False, default=False)

    customer_code = fields.Char(string='Customer Code',

                                copy=False,
                                readonly=True,
                                index=True, )

    @api.onchange('partner_id')
    def customer_code_partner(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_code = rec.partner_id.customer_code

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('approve_sale', 'Quotation Approve'),
        ('approve', 'Approve'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    def action_delivery_approve(self):
        for rec in self:
            rec.state = 'approve'
            rec.is_delivery_approve = True

    def reset_to_draft(self):
        self.state = 'draft'


class AccountPaymentTermInherit(models.Model):
    _inherit = 'account.payment.term'

    is_immediate = fields.Boolean(string="Immediate")


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    invoice_state = fields.Selection('sale.order', string="Invoice State", readonly=True, related='sale_id.invoice_status')


    # @api.onchange('invoice_status')
    # def get_invoice_status(self):
    #     # for rec in self:
    #     res = self.env['sale.order'].search([('id', '=', self.sale_id.id)])
    #     for line in res:
    #         print("LLLLLLLLL", line)
    #         if self.sale_id:
    #             for inv in line.invoice_ids:
    #                 if inv.state:
    #                     self.invoice_state.update(inv.state)
    #                     print("YYYEEESSSS", self.invoice_state, inv.state)


    def button_validate(self):
        result = super(StockPickingInherit, self).button_validate()
        res = self.env['sale.order'].search([('id', '=', self.sale_id.id)])
        if res:
            for line in res:
                if line.payment_term_id.is_immediate:
                    if line.invoice_ids:
                        for inv in line.invoice_ids:
                            if not inv.payment_state == 'paid':
                                raise ValidationError(_('The Invoice Must Be Paid'))
                    else:
                        raise ValidationError(_('The Invoice Must Be Paid'))

        return result
