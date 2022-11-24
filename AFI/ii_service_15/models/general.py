##############################################################################
#    Description: Job Order                                                  #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import Warning, UserError


###########################################
# Modifying model to add job order counters
class ResPartner(models.Model):
    _inherit = 'res.partner'

    job_ids = fields.One2many('job.order', 'customer_id', 'Job Order(s)')
    job_count = fields.Integer(compute='_get_job_count', string='Job Order(s)')
    engineer = fields.Boolean('Is Engineer?', default=False)
    technician = fields.Boolean('Is Technician?', default=False)

    def _get_job_count(self):
        jobs = self.env['job.order']
        for rec in self:
            rec.job_count = 0
            jobs_ids = jobs.search([('customer_id', '=', rec.id)])
            rec.job_count = len(jobs_ids.ids)


###############################################
# inheriting to add search function as well as link to job order
class SaleOrder(models.Model):
    _inherit = "sale.order"

    job_order = fields.Many2one('job.order', 'Job Order', readonly=True)


###############################################
# inherited to add Meter Reading to Serial No. Model  #Job Order
class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    # @api.model
    # def default_get(self, fields):
    #     res = super(StockProductionLot, self).default_get(fields)
    #     active_model = self.env.context.get('active_model')
    #     print(active_model, 'bbbbbbb')
    #     job = self.env['job.order'].browse(self.env.context.get('active_id'))
    #     print(job, 'aaaaaac')
    #     return res

    # @api.model
    # def default_get(self, fields):
    #     result = super(StockProductionLot, self).default_get(fields)
    #     print('ccvvvcc')
    #     print('xxxxx',self._context)
    #     active_id = self._context.get('active_id')
    #     print('ccvvvcc',active_id)
    #     result['job_id'] = self._context.get('active_id')
    #     if self.env.context.get('active_id') and self.env.context.get('active_model') == 'job.order':
    #         payslip_id = self.env.context['active_id']
    #         print('cccc',self.env.context.get('active_id'))
    #         print('nnnn',payslip_id)
    #         payslip = self.env['job.order'].browse(payslip_id)
    #         if 'product_id' in fields:
    #             result['job_id'] = payslip_id
    #             result['product_id'] = payslip.product_id.id
    #     # res = super(StockProductionLot, self).default_get(fields)
    #     # print('hgffdd')
    #     # active_model = self.env.context.get('active_model')
    #     # po = self.env['job.order'].browse(self.env.context.get('active_ids'))
    #     # ('modelgggg', active_model)
    #     # ('modelgggg', po)
    #     # if active_model == 'job.order':
    #     #     contract_id = self.env.context.get('active_id')
    #     #     ('contract_idgggg', contract_id)
    #     #     job = self.env['job.order'].sudo().browse(contract_id)
    #     #     ('contract_idgggg', job)
    #     #     if job:
    #     #         res.update({
    #     #             # 'job_id': job.id,
    #     #             'product_id': job.tractor_id.id,
    #     #         })
    #     return result

    # @api.model
    # def create(self, vals):
    #     res = super(StockProductionLot, self).create(vals)
    #     print('\n\n +++++++++++++ order_id',self.env.context.get('order_id'))
    #     # active_model = self.env.context.get('active_model')
    #     # print(active_model,'bbbbbbb')
    #     # job = self.env['job.order'].browse(self.env.context.get('active_ids'))
    #     # print(job,'aaaaaac')
    #     # # if active_model == 'job.order' and len(self.env.context.get('active_ids', [])) <= 1:
    #     # #     jobs = self.env[active_model].browse(self.env.context.get('active_id')).exists()
    #     # #     print(jobs,'jjjjjjjjjjjjj')
    #     # #     if jobs:
    #     # #         res.update({
    #     # #             'job_id': jobs.id,
    #     # #             'product_id': jobs.tractor_id.id,
    #     # #         })
    #     return res


    # act_model = self.env.context.get('active_model')
    # active_model_id = self.env['ir.model'].search([('name', '=', act_model)]).id
    # filtered_report = self.env['ir.actions.report'].search([('binding_model_id', '=', active_model_id)], limit=1)

    meter_reading = fields.Float('Meter Reading')
    job_id = fields.Many2one('job.order', 'Job Ref')
    company_id = fields.Many2one('res.company', 'Company',default=lambda self: self.env.company, required=True, store=True, index=True)
    # job_id = fields.Many2one('job.order', 'Job Ref',default=lambda self: self.env.context.get('active_id', None))
    product_id = fields.Many2one(
        'product.product', 'Product', index=True,domain=[('is_spare_parts', '=', False)],
        required=True, check_company=True)

    # def _domain_product_id(self):
    #     active_model = self.env.context.get('active_model')
    #     if active_model in ('product.template', 'product.product') and self.env.context.get('active_id'):
    #         product = self.env[active_model].browse(self.env.context.get('active_id'))
    #         product = product.exists()
    #         if product:
    #             return [('id', '=', product.categ_id.id)]
    #     return []

################################################
# Inherited to add warehouse config in settings
class ResCompany(models.Model):
    _inherit = 'res.company'

    service_id = fields.Many2one('product.product', string='Service Config', domain=[('type', '=', 'service')])
    travel_id = fields.Many2one('product.product', string='Travel Config', domain=[('type', '=', 'service')])
    source_warehouse_id = fields.Many2one('stock.warehouse', 'From Warehouse')
    temp_warehouse_id = fields.Many2one('stock.warehouse', 'Temp Warehouse')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    service_id = fields.Many2one('product.product', string='Service Config', domain=[('type', '=', 'service')],
                                 related='company_id.service_id', readonly=False)
    travel_id = fields.Many2one('product.product', string='Travel Config', domain=[('type', '=', 'service')],
                                related='company_id.travel_id', readonly=False)
    source_warehouse_id = fields.Many2one('stock.warehouse', 'From Warehouse', related='company_id.source_warehouse_id',
                                          readonly=False)
    temp_warehouse_id = fields.Many2one('stock.warehouse', 'Temp Warehouse', related='company_id.temp_warehouse_id',
                                        readonly=False)


###############################################
# inherited to add Job in stock.picking
class StockPicking(models.Model):
    _inherit = "stock.picking"

    job_id = fields.Many2one('job.order', 'Job Ref')


#####################################################
# inherited to add Job in product.product 
class ProductInherit(models.Model):
    _inherit = 'product.product'

    is_spare_parts = fields.Boolean(string="Spare Parts", default=False)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_spare_parts = fields.Boolean(string="Spare Part", default=False)
