##############################################################################
#    Description: General Base Customization                                 #
#    Author: IntelliSoft Software                                            #
#    Date: February 2017                                                     #
##############################################################################

from odoo import models, fields, api, _


# inheritance to add fields
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    MPN = fields.Many2many('product.template', 'product_product_rel', 'product_id', 'product_compatible_id',
                           string='MPN')
    loc_case = fields.Char(string='Case')
