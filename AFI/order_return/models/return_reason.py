# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ReturnReason(models.Model):
    _name = 'return.reason'
    _rec_name = 'name'
    _description = 'Purchase Return Reason'

    name = fields.Char(string="Name", required=False, )
