# -*- coding: utf-8 -*-
# from odoo import http


# class IiJournalEntryChangeCurrencyRate(http.Controller):
#     @http.route('/ii_journal_entry_change_currency_rate/ii_journal_entry_change_currency_rate/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ii_journal_entry_change_currency_rate/ii_journal_entry_change_currency_rate/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ii_journal_entry_change_currency_rate.listing', {
#             'root': '/ii_journal_entry_change_currency_rate/ii_journal_entry_change_currency_rate',
#             'objects': http.request.env['ii_journal_entry_change_currency_rate.ii_journal_entry_change_currency_rate'].search([]),
#         })

#     @http.route('/ii_journal_entry_change_currency_rate/ii_journal_entry_change_currency_rate/objects/<model("ii_journal_entry_change_currency_rate.ii_journal_entry_change_currency_rate"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ii_journal_entry_change_currency_rate.object', {
#             'object': obj
#         })
