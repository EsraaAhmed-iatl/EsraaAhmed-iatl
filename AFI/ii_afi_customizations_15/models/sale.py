##############################################################################
#    Description: Stock Customization                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import except_orm, Warning
import odoo.addons.decimal_precision as dp
from odoo import SUPERUSER_ID


# inherited to add Beneficiary to invoice
class AccountInvoice(models.Model):
    _inherit = "account.move"

    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary',
                                     help='Beneficiary in case of purchase though bank.')

    is_com_header = fields.Boolean('Company Header?', default=False)

    # To Get Beneficiary From Invoice To Voucher , edit in dictionary
    def invoice_pay_customer(self):
        res = super(AccountInvoice, self).invoice_pay_customer()
        res['context']
        beneficiary_id = self.beneficiary_id.id
        res['context'].update({
            'default_beneficiary_id': beneficiary_id,
        })
        return res


#########################################################################
# inherited to Get Beneficiary From Sale Order To Invoice
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_from = fields.Date("Date From", _compute="lambda *a,k:{}")
    date_to = fields.Date("Date To", _compute="lambda *a,k:{}")
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary',
                                     help='Beneficiary in case of purchase though bank.')
    finance_state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('app', 'Loan Application'),
        ('rfl', 'Requested Final Invoice'),
        ('cp', 'Contract Preparation'),
        ('cs', 'Contract Signature'),
        ('ir', 'Insurance and Registration'),
        ('cancel', 'Cancelled'),
        ('cr', 'Cash Released')], 'Finance Status', copy=False, help="Used to track finance status", default='draft')
    finance_tracker = fields.Boolean('Track Finance?', default=False)
    # discount_amount = fields.Float(compute="_get_discount_line", string="Total Discount")
    is_com_header = fields.Boolean('Company Header?', default=False)
    vat_tax_id = fields.Many2many('account.tax', 'sale_order_vat', 'order_id', 'tax_id', 'Taxes')
    
    quotations_date = fields.Date(string="Quotations Date", required=False, default=fields.Date.context_today)
    code_customer = fields.Char(string="Customer Code", readonly=True)

    @api.onchange('partner_id')
    def get_customer_code(self):
        for rec in self:
            if rec.partner_id:
                rec.code_customer = rec.partner_id.customer_code

    # prepare invoice
    @api.model
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'beneficiary_id': self.beneficiary_id.id,
        })
        return invoice_vals

    # To genrate VAT to Product
    def generate_vat_tax(self):
        for order in self:
            vat_tax_id = order.vat_tax_id
            for line in order.order_line:
                line.tax_id = vat_tax_id
                line.sudo().write({'tax_id': vat_tax_id})

    # # proceed directly and create invoice without popping up wizard
    # def action_confirm(self):
    #     res = super(SaleOrder, self).action_confirm()
    #     #####################################################
    #     ctx = dict(self._context)
    #     ctx.update({'active_ids': self.ids})
    #     wizard_dict = {'advance_payment_method': 'delivered'}
    #     wizard = self.env['sale.advance.payment.inv'].create(wizard_dict)
    #     wizard.with_context(ctx).create_invoices()
    #     return res
