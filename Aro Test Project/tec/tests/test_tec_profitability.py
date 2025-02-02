# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestTecProfitabilityCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Georges',
            'email': 'georges@tec-profitability.com'})

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan A',
            'company_id': False,
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Tec - AA',
            'code': 'AA-1234',
            'plan_id': cls.analytic_plan.id,
        })
        cls.tec = cls.env['tec.tec'].with_context({'mail_create_nolog': True}).create({
            'name': 'Tec',
            'partner_id': cls.partner.id,
            'analytic_account_id': cls.analytic_account.id,
        })
        cls.task = cls.env['tec.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Task',
            'tec_id': cls.tec.id,
        })
        cls.tec_profitability_items_empty = {
            'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [], 'total': {'billed': 0.0, 'to_bill': 0.0}},
        }


class TestProfitability(TestTecProfitabilityCommon):
    def test_tec_profitability(self):
        """ Test the tec profitability has no data found

            In this module, the tec profitability should have no data.
            So the no revenue and cost should be found.
        """
        profitability_items = self.tec._get_profitability_items(False)
        self.assertDictEqual(
            profitability_items,
            self.tec_profitability_items_empty,
            'The profitability data of the tec should be return no data and so 0 for each total amount.'
        )
