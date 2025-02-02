# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestTecUpdateUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Enable the "Milestones" feature to be able to create milestones on this tour.
        cls.env['res.config.settings'] \
            .create({'group_tec_milestone': True}) \
            .execute()

    def test_01_tec_tour(self):
        self.start_tour("/web", 'tec_update_tour', login="admin")
