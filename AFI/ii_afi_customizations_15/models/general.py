##############################################################################
#    Description: General Base Customization                                 #
#    Author: IntelliSoft Software                                            #
#    Date: February 2017                                                     #
##############################################################################

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_header = fields.Binary('Report Headers')
    company_footer = fields.Binary('Report Footers')
