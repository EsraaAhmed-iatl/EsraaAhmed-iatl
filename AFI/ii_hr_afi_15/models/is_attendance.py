# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, fields, api, exceptions, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class HrMatwaAttendance(models.Model):
    _inherit = 'hr.attendance'

    lost_hours = fields.Float(string="Lost of Hours Cost", compute='compute_lost_hours', store=True, readonly=True)
    total_late = fields.Char(string="Lost Hours", compute='compute_lost_hours', readonly=True, store=True)
    reason = fields.Text(string="Comment")

    @api.depends('check_in', 'check_out')
    def compute_lost_hours(self):
        global check_in_hou_late, check_out_hou_late
        check_in_late = 0.0
        check_out_late = 0.0
        for attendance in self:
            attendance.total_late = 0
            attendance.lost_hours = 0
            if attendance.check_out:
                # check_in = str(attendance.check_in[10:])
                # check_out = str(attendance.check_out[10:])
                default_check_in = '05:00:00'
                default_check_out = '13:00:00'
                check_in_hou_late = 0.0
                check_out_hou_late = 0.0
                check_in_late = 0.0
                check_out_late = 0.0
                total_late = '00.00.00'
                check_in_date = attendance.check_in
                check_out_date = attendance.check_out
                check_in_date = str(check_in_date.date())
                check_out_date = str(check_out_date.date())

                def_check_in = check_in_date + ' ' + default_check_in
                def_check_out = check_out_date + ' ' + default_check_out
                print(str(attendance.check_in), def_check_in)
                if str(attendance.check_in) <= def_check_in:
                    check_in_late = 0.0
                if str(attendance.check_in) >= def_check_in:
                    check_in_late = attendance.check_in - datetime.strptime(def_check_in, DEFAULT_SERVER_DATETIME_FORMAT)
                    # check_in_late = check_in_late[10:]
                    check_in_hou_late = check_in_late.total_seconds() / 3600.0
                print(str(attendance.check_out), def_check_out)
                if str(attendance.check_out) >= def_check_out:
                    check_out_late = 0.0
                if str(attendance.check_out) <= def_check_out:
                    check_out_late = datetime.strptime(def_check_out, DEFAULT_SERVER_DATETIME_FORMAT) - attendance.check_out
                    check_out_hou_late = check_out_late.total_seconds() / 3600
                if check_in_late == 0.0:
                    total_late = check_out_late
                elif check_out_late == 0.0:
                    total_late = check_in_late
                else:
                    total_late = check_in_late + check_out_late
                attendance.total_late = total_late
                attendance.lost_hours = check_in_hou_late + check_out_hou_late

