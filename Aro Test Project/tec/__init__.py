# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import populate

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import create_index


def _check_exists_collaborators_for_tec_sharing(env):
    """ Check if it exists at least a collaborator in a shared tec

        If it is the case we need to active the portal rules added only for this feature.
    """
    collaborator = env['tec.collaborator'].search([], limit=1)
    if collaborator:
        # Then we need to enable the access rights linked to tec sharing for the portal user
        env['tec.collaborator']._toggle_tec_sharing_portal_rules(True)


def _tec_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _check_exists_collaborators_for_tec_sharing(env)

    # Index to improve the performance of burndown chart.
    tec_task_stage_field_id = env['ir.model.fields']._get_ids('tec.task').get('stage_id')
    create_index(
        cr,
        'mail_tracking_value_mail_message_id_old_value_integer_task_stage',
        env['mail.tracking.value']._table,
        ['mail_message_id', 'old_value_integer'],
        where=f'field={tec_task_stage_field_id}'
    )
