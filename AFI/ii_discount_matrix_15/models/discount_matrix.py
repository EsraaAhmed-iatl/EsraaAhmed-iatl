# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

import babel
import time
import datetime
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError


class DiscountMatrix(models.Model):
    _name = 'discount.matrix'
    _inherit = ['mail.thread']

    name = fields.Char('Reference', required=True)
    date_from = fields.Date(string='Date From',  required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    level_line_ids = fields.One2many('discount.matrix.line', 'matrix_id', 'Levels')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('discount.matrix'))

    @api.onchange('date_from', 'date_to')
    def get_date(self):
        for x in self:
            if x.date_to and x.date_from:
                first_date = datetime.fromtimestamp(time.mktime(time.strptime(str(x.date_from), "%Y-%m-%d")))
                second_date = datetime.fromtimestamp(time.mktime(time.strptime(str(x.date_to), "%Y-%m-%d")))
                locale = self.env.context.get('lang', 'en_US')
                if (first_date.month == second_date.month) and (first_date.year == second_date.year):
                    x.name = 'Discount Matrix For ' + ' ' + \
                    tools.ustr(babel.dates.format_date(date=first_date, format='MMMM-y', locale=locale)) 
                else:
                    x.name = 'Discount Matrix From ' + ' ' + \
                    tools.ustr(babel.dates.format_date(date=first_date, format='MMMM-y', locale=locale)) \
                    + ' ' + 'To' + ' ' + \
                    tools.ustr(babel.dates.format_date(date=second_date, format='MMMM-y', locale=locale))

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Discount Matrix Already Exists In This Period!"),
    ]


class DiscountMatrixLine(models.Model):
    _name = 'discount.matrix.line'
    _inherit = ['mail.thread']
    _rec_name = 'position_id'

    name = fields.Char(string='Discount Level', tracking=5)
    position_id = fields.Many2one('hr.job', 'Jop Position', required=True)
    min_allowed = fields.Float(string='Min Allowed Discount (%) ', required=True, tracking=5)
    max_allowed = fields.Float(string='Max Allowed Discount (%) ', required=True, tracking=5)
    matrix_id = fields.Many2one('discount.matrix', 'Discount Matrix')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('discount.matrix.line'))

    @api.constrains('name', 'position_id')
    def _check_position_level(self):
        for level in self:
            level_check = self.env['discount.matrix.line'].search([
                ('matrix_id', '=', level.matrix_id.id),
                ('name', '=', level.name),('position_id', '=', level.position_id.id),
                ('id', '!=', level.id),
            ])
            if level.name and level.position_id and level_check:
                raise ValidationError(_("this position is already have level."))