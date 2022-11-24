# -*- coding: utf-8 -*-
# from odoo import http


# class IiSoConfigApprove(http.Controller):
#     @http.route('/ii_so_config_approve_15/ii_so_config_approve_15/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ii_so_config_approve_15/ii_so_config_approve_15/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ii_so_config_approve_15.listing', {
#             'root': '/ii_so_config_approve_15/ii_so_config_approve_15',
#             'objects': http.request.env['ii_so_config_approve_15.ii_so_config_approve_15'].search([]),
#         })

#     @http.route('/ii_so_config_approve_15/ii_so_config_approve_15/objects/<model("ii_so_config_approve_15.ii_so_config_approve_15"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ii_so_config_approve_15.object', {
#             'object': obj
#         })
