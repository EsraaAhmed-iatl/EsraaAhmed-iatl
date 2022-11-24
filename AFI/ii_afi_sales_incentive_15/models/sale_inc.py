# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError


class SaleIncentive(models.Model):
    _name = 'sale.incentive'
    _inherit = ['mail.thread']

    name = fields.Char('Reference', required=True)
    line_ids = fields.One2many('sale.incentive.line', 'inc_id', 'Levels')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.incentive'))


class SaleIncentiveLine(models.Model):
    _name = 'sale.incentive.line'
    _inherit = ['mail.thread']
    _rec_name = 'position_id'

    position_id = fields.Many2one('hr.job', 'Position', required=True)
    commission = fields.Float(string='Commission (%) ', required=True, tracking=5)
    inc_id = fields.Many2one('sale.incentive', 'Incentive')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('discount.matrix.line'))

    level1_check = fields.Boolean('Sale Rep?', default=False)
    level2_check = fields.Boolean('Team Leader?', default=False)
