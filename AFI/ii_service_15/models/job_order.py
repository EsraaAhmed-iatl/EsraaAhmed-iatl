##############################################################################
#    Description: Job Order                                                  #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import Warning,UserError,ValidationError


class JobOrder(models.Model):
    _name = 'job.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Create a job order.'
    _rec_name = 'job_no'

    # def _default_service(self):
    #     return self.env.company.service_id
    stock_picking_count = fields.Integer(string='# of Stock Picking', compute='get_stock_picking', readonly=True)
    stock_picking_ids = fields.One2many('stock.picking', 'job_id', readonly=True)
    sale_order_count = fields.Integer(string='# of Sale Orders', compute='get_sale_order_per_job', readonly=True)
    sale_order_ids = fields.One2many('sale.order', 'job_order', readonly=True)
    job_no = fields.Char('Job No.', help='Auto-generated Job No. for Job Order')
    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    sales_id = fields.Many2one('sale.order', 'Sale Reference', readonly=True)
    customer_id = fields.Many2one('res.partner', 'Customer', required=True)
    complaint_date = fields.Datetime('Complaint Date', required=True, default=datetime.now())
    start_date = fields.Datetime('Start Date', default=lambda self: fields.Date.today())
    end_date = fields.Datetime('End Date')
    customer_contact = fields.Char('Telephone', related='customer_id.phone')
    tractor_id = fields.Many2one('product.product',
                                 domain=[('is_spare_parts', '=', False)],
                                 string='Tractor', required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Serial No.', domain="[('product_id', '=', tractor_id)]")
    lot_name = fields.Char('Serial Name')
    engineer_ids = fields.Many2many('res.partner', 'order_engineers_rel', 'engineer_id', 'order_id', string='Engineer', domain=[('engineer', '=', True)])
    technician_ids = fields.Many2many('res.partner', 'order_technicians_rel', 'technician_id', 'order_id',string='Technician', domain=[('technician', '=', True)])
    meter_reading = fields.Float('Meter Reading', related='lot_id.meter_reading')
    warranty = fields.Selection(selection=[('covered', 'Covered'), ('not-covered', 'Not Covered')], string='Warranty',
                                default='not-covered')
    job_order_type = fields.Selection(selection=[('inside', 'Inside Workshop'), ('outside', 'Outside Workshop')],
                                      string='Job Order Type', default='inside')
    customer_location = fields.Char('Location')
    complaint_detail_ids = fields.One2many('complaint.detail', 'job_order_id', string='Complaint Detail(s)')
    service_details_ids = fields.One2many('service.detail', 'job_order_id', string='Service Detail(s)')
    aservice_details_ids = fields.One2many('service.adetail', 'job_order_id', string='Additional Service Detail(s)')
    spare_part_details_ids = fields.One2many('spare.part', 'job_order_id', string='Spare Part(s)')
    travel_exp = fields.Float('Travel Expenses(SDG)')
    service_id = fields.Many2one('product.product', string='Service', domain=[('type', '=', 'service')], required=True, default=lambda self: self.env.user.company_id.service_id.id)
    travel_id = fields.Many2one('product.product', string='Travel', domain=[('type', '=', 'service')], default=lambda self: self.env.user.company_id.travel_id.id)
    total_service_hours = fields.Float('Total Service Hour(s)', default=0, compute='get_totals', readonly=True)
    total_service_cost = fields.Float('Total Service Cost(SDG)', default=0, compute='get_totals', readonly=True, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('sales', 'Sales')
    ], default='draft')
    source_warehouse_id = fields.Many2one('stock.warehouse', 'From Warehouse', default=lambda self: self.env.user.company_id.source_warehouse_id.id)
    temp_warehouse_id = fields.Many2one('stock.warehouse', 'Temp Warehouse', default=lambda self: self.env.user.company_id.temp_warehouse_id.id)

    @api.model
    def create(self, vals):
        res = super(JobOrder, self).create(vals)
        if not res.lot_id:
            if not res.tractor_id.tracking == 'serial':
                raise ValidationError(_("you Tractor must be Tracjed by lot ! Please check the tractor Profile!"))
            else:
                lot_obj = self.env['stock.production.lot']
                production_lot_vals = {'name': res.lot_name,
                                       'product_id': res.tractor_id.id,
                                       'meter_reading': res.meter_reading,
                                       'job_id': res.id}
                lot_id = lot_obj.create(production_lot_vals)
                res.lot_id = lot_id
        else:
            self.lot_name = False
        return res

    def write(self, vals):
        res = super(JobOrder, self).write(vals)
        if self.lot_name:
            if not self.lot_id:
                if not self.tractor_id.tracking == 'serial':
                    raise ValidationError(_("you Tractor must be Tracked by Unique Serial Number! Please check the tractor Profile!"))
                else:
                    lot_obj = self.env['stock.production.lot']
                    production_lot_vals = {'name': self.lot_name,
                                           'product_id': self.tractor_id.id,
                                           'meter_reading': self.meter_reading,
                                           'job_id': self.id}
                    lot_id = lot_obj.create(production_lot_vals)
                    self.lot_id = lot_id
            else:
                self.lot_name = False
        return res

    # get product serial number
    @api.onchange('tractor_id')
    def get_tractor_serial_number(self):
        for rec in self:
            lots = self.env['stock.production.lot'].search([('product_id', '=', rec.tractor_id.id)])
            if lots:
                for lot in lots:
                    if lot:
                        if rec.tractor_id:
                            rec.lot_id = lot.id
            else:
                rec.lot_id = False

    # # onchange Tractor
    # @api.onchange('lot_id')
    # def get_tractor(self):
    #     if self.lot_id:
    #         self.tractor_id = self.lot_id.product_id.id

    #counter of stock picking for the current job otder
    @api.depends('stock_picking_ids')
    def get_stock_picking(self):
        for picking in self:
            picking.update({
                'stock_picking_count': len(picking.stock_picking_ids),
            })

    # counter of sale orders for the current job order
    @api.depends('sale_order_ids')
    def get_sale_order_per_job(self):
        for orders in self:
            orders.update({
                'sale_order_count': len(orders.sale_order_ids),
        })

    def action_view_stock_picking(self):
        stock_picking_obj = self.env['stock.picking']
        stock_picking_ids = stock_picking_obj.search([('job_id', '=', self.id)])
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', stock_picking_ids.ids)]
        action['views'] = [(self.env.ref('stock.vpicktree').id, 'tree'),
                           (self.env.ref('ii_service_15.inherited_afi_view_picking_form').id, 'form')]
        action['res_id'] = stock_picking_ids.ids[0]
        return action

    def action_view_sale_orders(self):
        sale_order_obj = self.env['sale.order']
        sale_order_ids = sale_order_obj.search([('job_order', '=', self.id)])
        action = self.env.ref('ii_service_15.action_sale_order_job_order').read()[0]
        action['domain'] = [('id', 'in', sale_order_ids.ids)]
        action['views'] = [(self.env.ref('sale.view_quotation_tree_with_onboarding').id, 'tree'),
                           (self.env.ref('ii_service_15.inherited_view_sale_order_jobform').id, 'form')]
        action['res_id'] = sale_order_ids.ids[0]
        return action

    # Generate name of job order automatically
    @api.depends('customer_id', 'tractor_id', 'lot_id')
    def _get_description(self):
        self.name = (self.customer_id and ("Customer: " + self.customer_id.name) or " ") + "/" + (
            self.tractor_id and ("Product: " + self.tractor_id.name) or " ") + "/" + (
                        self.lot_id and ("Serial No.: " + str(self.lot_id.name)) or " ")

    # overriding default get
    @api.model
    def default_get(self, fields):
        res = super(JobOrder, self).default_get(fields)
        next_seq = self.env['ir.sequence'].get('workshop.job.no')
        res.update({'job_no': next_seq, })
        return res

    # def copy(self, default=None):
    #     default.update({'sale_id': ''})
    #     rec = super(JobOrder, self).copy(default=default)
    #     return rec

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning(_('User Error'), _("You are not allow to delete the Confirm and Done state records"))
        res = super(JobOrder, self).unlink()
        return res

    # Job confirmed
    def job_confirm(self):
        self.state = 'confirm'
        self.generate_picking()

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    # Close Job
    def job_done(self):
        self.state = 'done'

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def get_totals(self):
        # get total service hours and cost
        for recs in self:
            job_services = recs.env['service.detail'].search([('job_order_id', '=', recs.id)])
            tot_hours = 0
            tot_cost = 0
        for rec in job_services:
            tot_hours += rec.time_consumed
            tot_cost += rec.total

        recs.total_service_hours = tot_hours
        recs.total_service_cost = tot_cost

    # Generate quotation
    def job_sales_order(self):
        if self.end_date:
            # Sales order entry
            sale_order_vals = {'partner_id': self.customer_id.id,
                               'job_order': self.id,
                               'date_order': self.end_date,
                               'warehouse_id': self.temp_warehouse_id.id,
                               }
            self.sales_id = self.env['sale.order'].create(sale_order_vals)

            if self.sales_id and self.travel_exp > 0:
                # add travel expenses line
                sale_order_lines_vals = {'order_id': self.sales_id.id,
                                         'product_id': self.travel_id.id,
                                         'product_uom_qty': 1,
                                         'price_unit': self.travel_exp,
                                         }
                self.sales_id.order_line.create(sale_order_lines_vals)

            if self.sales_id and self.service_details_ids:
                # add service line
                sale_order_lines_vals = {'order_id': self.sales_id.id,
                                         'product_id': self.service_id.id,
                                         'product_uom_qty': 1,
                                         'price_unit': self.total_service_cost,
                                         }
                self.sales_id.order_line.create(sale_order_lines_vals)

            # add additional service lines
            if self.aservice_details_ids:
                for rec in self.aservice_details_ids:
                    sale_order_lines_vals = {'order_id': self.sales_id.id,
                                             'product_id': rec.service_id.id,
                                             'product_uom_qty': rec.unit_qty,
                                             'price_unit': rec.cost,
                                             }
                    self.sales_id.order_line.create(sale_order_lines_vals)

            # add products
            if self.spare_part_details_ids:
                for rec in self.spare_part_details_ids:
                    sale_order_lines_vals = {'order_id': self.sales_id.id,
                                             'product_id': rec.spare_part_id.id,
                                             'product_uom_qty': rec.qty,
                                             }
                    self.sales_id.order_line.create(sale_order_lines_vals)

            # Change state if all went well!
            self.state = 'sales'

            # Update footer message
            message_obj = self.env['mail.message']
            message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
            msg_id = self.message_post(body=message)
        else:
            raise UserError(_("An issue was faced generating a sales order! Please check End Date!"))

    # Generate Stock Picking
    def generate_picking(self):
        for rec in self:
            if rec.source_warehouse_id and rec.spare_part_details_ids:
                # Stock Picking order entry
                picking_id = self.env['stock.picking']
                stock_picking_vals = picking_id.create( {'partner_id': rec.customer_id.id,
                                      'location_dest_id': rec.temp_warehouse_id.lot_stock_id.id,
                                      'scheduled_date': rec.end_date,
                                      'job_id': rec.id,
                                      'origin': rec.job_no,
                                      'picking_type_id': rec.source_warehouse_id.out_type_id.id,
                                      'location_id': rec.source_warehouse_id.lot_stock_id.id,
                                      })
                for job in rec.spare_part_details_ids:
                    # Stock Move
                    self.env['stock.move'].create(
                            {'product_id': job.spare_part_id.id,
                            'product_uom_qty': job.qty,
                            'product_uom': job.spare_part_id.product_tmpl_id.uom_id.id,
                            'location_id': job.job_order_id.source_warehouse_id.lot_stock_id.id,
                            'name': job.spare_part_id.name,
                            'location_dest_id': job.job_order_id.temp_warehouse_id.lot_stock_id.id,
                            'picking_id': stock_picking_vals.id,
                            })

            else:
                raise UserError(_("An issue was faced generating a Picking! Please check Temp Warehouse or Spare Parts!"))


####################################################################################################
class ComplaintDetail(models.Model):
    _name = 'complaint.detail'
    _description = 'Job order complaint details.'

    job_order_id = fields.Many2one('job.order', 'Job Order', required=True, ondelete='cascade')
    complaint_id = fields.Many2one('complaint.complaint', 'Complaint')
    notes = fields.Char('Notes')


########################################
class ComplaintComplaint(models.Model):
    _name = 'complaint.complaint'
    _description = 'Complaints.'

    name = fields.Char('Complaint', required=True)


##################################################
class ServiceDetail(models.Model):
    _name = 'service.detail'
    _description = 'Job order service details.'

    job_order_id = fields.Many2one('job.order', 'Job Order', required=True, ondelete='cascade')
    service_id = fields.Many2one('service.service', 'Service', required=True)
    time_consumed = fields.Float('Time Consumed', required=True)
    hour_rate = fields.Float('Hour Rate', related='service_id.rate', readonly=False)
    total = fields.Float(string='Total', compute='get_total')

    @api.depends('service_id', 'time_consumed', 'hour_rate')
    def get_total(self):
        for rec in self:
            rec.total = 0.0
            if rec.service_id and rec.time_consumed and rec.hour_rate:
                rec.total = rec.time_consumed * rec.hour_rate


####################################
class ServiceService(models.Model):
    _name = 'service.service'
    _description = 'Service.'

    name = fields.Char('Service', required=True)
    rate = fields.Float('Hour Rate')


####################################
class ServiceAdetail(models.Model):
    _name = 'service.adetail'
    _description = 'Job order additional service details.'

    job_order_id = fields.Many2one('job.order', 'Job Order', required=True, ondelete='cascade')
    service_id = fields.Many2one('product.product', 'Additional Service', domain=[('type', '=', 'service')],
                                 required=True)
    # time_consumed = fields.Float('Time Consumed', required=True)
    unit_qty = fields.Integer('unit QTY',)
    cost = fields.Float(string='Unit Cost')
    total = fields.Float(string='Total', compute='get_total')

    @api.depends('service_id', 'unit_qty', 'cost')
    def get_total(self):
        for rec in self:
            rec.total = 0.0
            if rec.service_id and rec.unit_qty and rec.cost:
                rec.total = rec.unit_qty * rec.cost


###############################
class SparePart(models.Model):
    _name = 'spare.part'
    _description = 'Spare part(s) from warehouse'

    job_order_id = fields.Many2one('job.order', 'Job Order', required=True, ondelete='cascade')
    spare_part_id = fields.Many2one('product.product', 'Spare Part', domain=[('type', '=', 'product')], required=True)
    qty = fields.Float('Qty', default=1)
    delivered = fields.Boolean('Delivered?')
    notes = fields.Char('Notes')
