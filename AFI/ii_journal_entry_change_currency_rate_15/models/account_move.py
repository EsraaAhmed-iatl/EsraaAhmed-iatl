# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL International Pvt. Ltd.
#    Copyright (C) 2020-TODAY Tech-Receptives(<http://www.iatl-sd.com>).
#
###############################################################################

from odoo import fields, models, api


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    custom_rate = fields.Float('Currency Rate', default=0.0,
                               )

    #
    @api.onchange('line_ids', 'custom_rate', 'line_ids.amount_currency')
    def set_custom_rate(self):
        for rec in self:
            if rec.line_ids:
                for line in rec.line_ids:
                    line.custom_rate = rec.custom_rate
                line._onchange_amount_currency()
    #                 if line.amount_currency:
    #                     if line.custom_rate / line.amount_currency > 0:
    #                         line.debit = line.custom_rate / line.amount_currency
    #                     else:
    #                         line.credit = line.custom_rate / line.amount_currency


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    custom_rate = fields.Float('Custom Rate',
                               )

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        # balance=0.0
        for line in self:
            print('---------------line.amount_currency', line.amount_currency)

            company = line.move_id.company_id
            balance = line.currency_id._convert(line.amount_currency, company.currency_id, company,
                                                line.move_id.date or fields.Date.context_today(line))
            # print('---------------line.balance', balance)
            # print('---------------line.line.currency_id', line.currency_id)
            if line.custom_rate:
                balance = line.amount_currency / line.custom_rate
                print('---------------self.custom_rate', line.custom_rate)
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())
    # currency_rate = fields.Float('Currency Rate',
    #                              # compute="_get_currency_rate"
    #                              )

    # @api.depends('custom_rate')
    # def _get_currency_rate(self):
    #     """
    #     get acctual Currency Rate As 1/custom_rate
    #     """
    #     for rec in self:
    #         if rec.custom_rate:
    #             rec.currency_rate = 1 / rec.custom_rate

    # @api.onchange('amount_currency', 'custom_rate', 'currency_rate')
    # def _onchange_amount_currency(self):
    #     """Overrides _onchange_amount_currency(), That Recompute the debit/credit
    #     based on amount_currency/currency_id and date to include custom rate in
    #     currency related calculations represented in the context
    #     """
    #     res = super(AccountMoveLine, self.with_context(custom_rate=self.currency_rate))._onchange_amount_currency()
    #     return res

    # @api.onchange('currency_id')
    # def _onchange_currency(self):
    #     """Overrides _onchange_currency() ,Update custom rate value on change of
    #     currency_id/custom_rate values
    #     """
    #
    #     move_type = self._context.get('default_type')
    #     for rec in self:
    #         res = super(AccountMoveLine, rec.with_context(custom_rate=rec.currency_rate))._onchange_currency()
    #         today = fields.Date.today()
    #
    #         if rec.currency_id and move_type == 'entry':
    #             rec.custom_rate = rec.currency_id._get_conversion_rate(rec.currency_id,
    #                                                                    rec.move_id.company_id.currency_id,
    #                                                                    rec.move_id.company_id,
    #                                                                    rec.move_id.date or today)
    #         return res

    # def _recompute_debit_credit_from_amount_currency(self):
    #     """Overrides _recompute_debit_credit_from_amount_currency(), That Recompute the debit/credit
    #     based on amount_currency/currency_id and date to include custom rate in
    #     currency related calculations represented in the context
    #     """
    #
    #     """" in upgrading to 14 this function has been deprecated so we copy it here"""
    #     for line in self:
    #         # Recompute the debit/credit based on amount_currency/currency_id and date.
    #
    #         company_currency = line.account_id.company_id.currency_id
    #         balance = line.amount_currency
    #         if line.currency_id and company_currency and line.currency_id != company_currency:
    #             balance = line.currency_id._convert(balance, company_currency, line.account_id.company_id,
    #                                                 line.move_id.date or fields.Date.today())
    #             line.debit = balance > 0 and balance or 0.0
    #             line.credit = balance < 0 and -balance or 0.0

    # @api.onchange('custom_rate')
    # def _onchange_custom_rate(self):
    #     for rec in self:
    #         rec.with_context(custom_rate=rec.currency_rate)._recompute_debit_credit_from_amount_currency()

    # @api.depends('custom_rate')
    # def _get_currency_rate(self):
    #     """
    #     get acctual Currency Rate As 1/custom_rate
    #     """
    #     for rec in self:
    #         rec.currency_rate = 1 / rec.custom_rate

    # @api.onchange('amount_currency', 'custom_rate', 'currency_rate')
    # def _onchange_amount_currency(self):
    #     """Overrides _onchange_amount_currency(), That Recompute the debit/credit
    #     based on amount_currency/currency_id and date to include custom rate in
    #     currency related calculations represented in the context
    #     """
    #     res = super(AccountMoveLine, self.with_context(custom_rate=self.currency_rate))._onchange_amount_currency()
    #     return res
