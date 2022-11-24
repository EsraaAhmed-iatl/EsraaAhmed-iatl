# -*- coding: utf-8 -*-
###########

from odoo import api, fields, models, _
import xlsxwriter
import base64
import datetime
from io import StringIO, BytesIO
from datetime import *
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from dateutil import relativedelta





class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_account = fields.Many2one('account.account', string="Debit Account")
    bank_acc = fields.Char("Bank Account")



class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    employee_account = fields.Many2one(readonly=True)
    bank_acc = fields.Char(readonly=True)