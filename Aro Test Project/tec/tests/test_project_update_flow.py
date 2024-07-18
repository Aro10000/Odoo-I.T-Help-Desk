# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.tec.tests.test_tec_base import TestTecCommon

@tagged('-at_install', 'post_install')
class TestTecUpdate(TestTecCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.config.settings'] \
            .create({'group_tec_milestone': True}) \
            .execute()

    def test_tec_update_form(self):
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today()

        try:
            with Form(self.env['tec.update'].with_context({'default_tec_id': self.tec_pigs.id})) as update_form:
                update_form.name = "Test"
                update_form.progress = 65
            update = update_form.save()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while filling the tec update form ! Exception : " + e.args[0])

        self.assertEqual(update.user_id, self.env.user, "The author is the user who created the update.")
        self.assertNotEqual(len(update.description), 0, "The description should not be empty.")
        self.assertTrue("Activities" in update.description, "The description should contain 'Activities'.")
        self.assertEqual(update.status, 'on_track', "The status should be the default one.")

        with Form(self.env['tec.update'].with_context({'default_tec_id': self.tec_pigs.id})) as update_form:
            update_form.name = "Test 2"
        update = update_form.save()
        self.assertEqual(update.progress, 65, "The default progress is the one from the previous update by default")

    def test_tec_update_description(self):
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today()
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 2"
            milestone_form.deadline = fields.Date.today()
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 3"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=2)

        template_values = self.env['tec.update']._get_template_values(self.tec_pigs)

        self.assertTrue(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 2, "Milestone list length should be equal to 2")
        self.assertEqual(len(template_values['milestones']['created']), 3, "Milestone created length tasks should be equal to 3")

        self.tec_pigs.write({'allow_milestones': False})

        template_values = self.env['tec.update']._get_template_values(self.tec_pigs)

        self.assertFalse(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 0, "Milestone list length should be equal to 0 because the Milestones feature is disabled.")
        self.assertEqual(len(template_values['milestones']['created']), 0, "Milestone created length tasks should be equal to 0 because the Milestones feature is disabled.")

        self.tec_pigs.write({'allow_milestones': True})
        self.env['res.config.settings'] \
            .create({'group_tec_milestone': False}) \
            .execute()

        template_values = self.env['tec.update']._get_template_values(self.tec_pigs)

        self.assertFalse(template_values['milestones']['show_section'], 'The milestone section should not be visible since the feature is disabled')
        self.assertEqual(len(template_values['milestones']['list']), 0, "Milestone list length should be equal to 0 because the Milestones feature is disabled.")
        self.assertEqual(len(template_values['milestones']['created']), 0, "Milestone created length tasks should be equal to 0 because the Milestones feature is disabled.")

    def test_tec_update_panel(self):
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 1"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=-1)
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 2"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=-1)
            milestone_form.is_reached = True
        with Form(self.env['tec.milestone'].with_context({'default_tec_id': self.tec_pigs.id})) as milestone_form:
            milestone_form.name = "Test 3"
            milestone_form.deadline = fields.Date.today() + relativedelta(years=2)

        panel_data = self.tec_pigs.get_panel_data()

        self.assertEqual(len(panel_data['milestones']['data']), 3, "Panel data should contain 'milestone' entry")
        self.assertFalse(panel_data['milestones']['data'][0]['is_deadline_exceeded'], "Milestone is achieved")
        self.assertTrue(panel_data['milestones']['data'][1]['is_deadline_exceeded'], "Milestone is exceeded")
        self.assertTrue(panel_data['milestones']['data'][0]['is_reached'], "Milestone is done")
        self.assertFalse(panel_data['milestones']['data'][1]['is_reached'], "Milestone isn't done")
        # sorting
        self.assertEqual(panel_data['milestones']['data'][0]['name'], "Test 2", "Sorting isn't correct")
        self.assertEqual(panel_data['milestones']['data'][1]['name'], "Test 1", "Sorting isn't correct")
        self.assertEqual(panel_data['milestones']['data'][2]['name'], "Test 3", "Sorting isn't correct")

        # Disable the "Milestones" feature in the tec and check the "Milestones" section is not loaded for this tec.
        self.tec_pigs.write({'allow_milestones': False})
        panel_data = self.tec_pigs.get_panel_data()
        self.assertNotIn('milestones', panel_data, 'Since the "Milestones" feature is disabled in this tec, the "Milestones" section is not loaded.')

        # Disable globally the Milestones feature and check the Milestones section is not loaded.
        self.tec_pigs.write({'allow_milestones': True})
        self.env['res.config.settings'] \
            .create({'group_tec_milestone': False}) \
            .execute()
        panel_data = self.tec_pigs.get_panel_data()
        self.assertNotIn('milestones', panel_data, 'Since the "Milestones" feature is globally disabled, the "Milestones" section is not loaded.')
