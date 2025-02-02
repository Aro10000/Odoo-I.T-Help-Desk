# -*- coding: utf-8 -*-

import ast

from datetime import date, datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class BiotechStage(models.Model):
    """ Model for case stages. This models the main stages of a Biotech Request management flow. """

    _name = 'biotech.stage'
    _description = 'Biotech Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Biotech Pipe')
    done = fields.Boolean('Request Done')


class BiotechEquipmentLocation(models.Model):
    _name = 'biotech.equipment.category'
    _inherit = ['mail.alias.mixin', 'mail.thread']
    _description = 'Biotech Equipment Location'

    @api.depends('equipment_ids')
    def _compute_fold(self):
        # fix mutual dependency: 'fold' depends on 'equipment_count', which is
        # computed with a read_group(), which retrieves 'fold'!
        self.fold = False
        for category in self:
            category.fold = False if category.equipment_count else True

    name = fields.Char('Location Name', required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    technician_user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self: self.env.uid)
    color = fields.Integer('Color Index')
    note = fields.Html('Comments', translate=True)
    equipment_ids = fields.One2many('biotech.equipment', 'category_id', string='Equipments', copy=False)
    equipment_count = fields.Integer(string="Equipment", compute='_compute_equipment_count')
    biotech_ids = fields.One2many('biotech.request', 'category_id', copy=False)
    biotech_count = fields.Integer(string="Biotech Count", compute='_compute_biotech_count')
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete='restrict', required=True,
        help="Email alias for this equipment category. New emails will automatically "
             "create a new equipment under this category.")
    fold = fields.Boolean(string='Folded in Biotech Pipe', compute='_compute_fold', store=True)

    def _compute_equipment_count(self):
        equipment_data = self.env['biotech.equipment']._read_group([('category_id', 'in', self.ids)], ['category_id'],
                                                                   ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in equipment_data])
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    def _compute_biotech_count(self):
        biotech_data = self.env['biotech.request']._read_group([('category_id', 'in', self.ids)], ['category_id'],
                                                               ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in biotech_data])
        for category in self:
            category.biotech_count = mapped_data.get(category.id, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_biotech_requests(self):
        for category in self:
            if category.equipment_ids or category.biotech_ids:
                raise UserError(_("You cannot delete an equipment category containing equipments or biotech requests."))

    def _alias_get_creation_values(self):
        values = super(BiotechEquipmentLocation, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('biotech.request').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['category_id'] = self.id
        return values


class BiotechEquipment(models.Model):
    _name = 'biotech.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Biotech Equipment'
    _check_company_auto = True

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'owner_user_id' in init_values and self.owner_user_id:
            return self.env.ref('biotech.mt_mat_assign')
        return super(BiotechEquipment, self)._track_subtype(init_values)

    def name_get(self):
        result = []
        for record in self:
            if record.name and record.serial_no:
                result.append((record.id, record.name + '/' + record.serial_no))
            if record.name and not record.serial_no:
                result.append((record.id, record.name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        equipment_ids = []
        if name and operator not in expression.NEGATIVE_TERM_OPERATORS and operator != '=':
            equipment_ids = self._search([('name', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return equipment_ids or super()._name_search(name, args, operator, limit, name_get_uid)

    name = fields.Char('Equipment Name', required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    technician_user_id = fields.Many2one('res.users', string='Technician', tracking=True)
    owner_user_id = fields.Many2one('res.users', string='Owner', tracking=True)
    category_id = fields.Many2one('biotech.equipment.category', string='Equipment Location',
                                  tracking=True, group_expand='_read_group_category_ids')
    partner_id = fields.Many2one('res.partner', string='Vendor', check_company=True)
    partner_ref = fields.Char('Vendor Reference')
    location = fields.Char('Location')
    model = fields.Char('Model')
    serial_no = fields.Char('Serial Number', copy=False)
    assign_date = fields.Date('Assigned Date', tracking=True)
    effective_date = fields.Date('Effective Date', default=fields.Date.context_today, required=True,
                                 help="Date at which the equipment became effective. This date will be used to compute the Mean Time Between Failure.")
    cost = fields.Float('Cost')
    note = fields.Html('Note')
    warranty_date = fields.Date('Warranty Expiration Date')
    color = fields.Integer('Color Index')
    scrap_date = fields.Date('Scrap Date')
    biotech_ids = fields.One2many('biotech.request', 'equipment_id')
    biotech_count = fields.Integer(compute='_compute_biotech_count', string="Biotech Count", store=True)
    biotech_open_count = fields.Integer(compute='_compute_biotech_count', string="Current Biotech", store=True)
    period = fields.Integer('Days between each preventive biotech')
    next_action_date = fields.Date(compute='_compute_next_biotech', string='Date of the next preventive biotech',
                                   store=True)
    biotech_team_id = fields.Many2one('biotech.team', string='Biotech Team', check_company=True)
    biotech_duration = fields.Float(help="Biotech Duration in hours.")

    @api.depends('effective_date', 'period', 'biotech_ids.request_date', 'biotech_ids.close_date')
    def _compute_next_biotech(self):
        date_now = fields.Date.context_today(self)
        equipments = self.filtered(lambda x: x.period > 0)
        for equipment in equipments:
            next_biotech_todo = self.env['biotech.request'].search([
                ('equipment_id', '=', equipment.id),
                ('biotech_type', '=', 'preventive'),
                ('stage_id.done', '!=', True),
                ('close_date', '=', False)], order="request_date asc", limit=1)
            last_biotech_done = self.env['biotech.request'].search([
                ('equipment_id', '=', equipment.id),
                ('biotech_type', '=', 'preventive'),
                ('stage_id.done', '=', True),
                ('close_date', '!=', False)], order="close_date desc", limit=1)
            if next_biotech_todo and last_biotech_done:
                next_date = next_biotech_todo.request_date
                date_gap = next_biotech_todo.request_date - last_biotech_done.close_date
                # If the gap between the last_biotech_done and the next_biotech_todo one is bigger than 2 times the period and next request is in the future
                # We use 2 times the period to avoid creation too closed request from a manually one created
                if date_gap > timedelta(0) and date_gap > timedelta(
                        days=equipment.period) * 2 and next_biotech_todo.request_date > date_now:
                    # If the new date still in the past, we set it for today
                    if last_biotech_done.close_date + timedelta(days=equipment.period) < date_now:
                        next_date = date_now
                    else:
                        next_date = last_biotech_done.close_date + timedelta(days=equipment.period)
            elif next_biotech_todo:
                next_date = next_biotech_todo.request_date
                date_gap = next_biotech_todo.request_date - date_now
                # If next biotech to do is in the future, and in more than 2 times the period, we insert an new request
                # We use 2 times the period to avoid creation too closed request from a manually one created
                if date_gap > timedelta(0) and date_gap > timedelta(days=equipment.period) * 2:
                    next_date = date_now + timedelta(days=equipment.period)
            elif last_biotech_done:
                next_date = last_biotech_done.close_date + timedelta(days=equipment.period)
                # If when we add the period to the last biotech done and we still in past, we plan it for today
                if next_date < date_now:
                    next_date = date_now
            else:
                next_date = equipment.effective_date + timedelta(days=equipment.period)
            equipment.next_action_date = next_date
        (self - equipments).next_action_date = False

    @api.depends('biotech_ids.stage_id.done')
    def _compute_biotech_count(self):
        for equipment in self:
            equipment.biotech_count = len(equipment.biotech_ids)
            equipment.biotech_open_count = len(equipment.biotech_ids.filtered(lambda x: not x.stage_id.done))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id and self.biotech_team_id:
            if self.biotech_team_id.company_id and not self.biotech_team_id.company_id.id == self.company_id.id:
                self.biotech_team_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.technician_user_id = self.category_id.technician_user_id

    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "Another asset already exists with this serial number!"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        for equipment in equipments:
            if equipment.owner_user_id:
                equipment.message_subscribe(partner_ids=[equipment.owner_user_id.partner_id.id])
        return equipments

    def write(self, vals):
        if vals.get('owner_user_id'):
            self.message_subscribe(partner_ids=self.env['res.users'].browse(vals['owner_user_id']).partner_id.ids)
        return super(BiotechEquipment, self).write(vals)

    @api.model
    def _read_group_category_ids(self, locations, domain, order):
        """ Read group customization in order to display all the locations in
            the kanban view, even if they are empty.
        """
        category_ids = locations._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return locations.browse(category_ids)

    def _prepare_biotech_request_vals(self, date):
        self.ensure_one()
        return {
            'name': _('Preventive Biotech - %s', self.name),
            'request_date': date,
            'schedule_date': date,
            'category_id': self.category_id.id,
            'equipment_id': self.id,
            'biotech_type': 'preventive',
            'owner_user_id': self.owner_user_id.id,
            'user_id': self.technician_user_id.id,
            'biotech_team_id': self.biotech_team_id.id,
            'duration': self.biotech_duration,
            'company_id': self.company_id.id or self.env.company.id
        }

    def _create_new_request(self, date):
        self.ensure_one()
        vals = self._prepare_biotech_request_vals(date)
        biotech_requests = self.env['biotech.request'].create(vals)
        return biotech_requests

    @api.model
    def _cron_generate_requests(self):
        """
            Generates biotech request on the next_action_date or today if none exists
        """
        for equipment in self.search([('period', '>', 0)]):
            next_requests = self.env['biotech.request'].search([('stage_id.done', '=', False),
                                                                ('equipment_id', '=', equipment.id),
                                                                ('biotech_type', '=', 'preventive'),
                                                                ('request_date', '=', equipment.next_action_date)])
            if not next_requests:
                equipment._create_new_request(equipment.next_action_date)


class BiotechRequest(models.Model):
    _name = 'biotech.request'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Biotech Request'
    _order = "id desc"
    _check_company_auto = True

    @api.returns('self')
    def _default_stage(self):
        return self.env['biotech.stage'].search([], limit=1)

    def _creation_subtype(self):
        return self.env.ref('biotech.mt_req_created')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return self.env.ref('biotech.mt_req_status')
        return super(BiotechRequest, self)._track_subtype(init_values)

    def _get_default_team_id(self):
        MT = self.env['biotech.team']
        team = MT.search([('company_id', '=', self.env.company.id)], limit=1)
        if not team:
            team = MT.search([], limit=1)
        return team.id

    name = fields.Char('Subjects', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    description = fields.Html('Description')
    request_date = fields.Date('Request Date', tracking=True, default=fields.Date.context_today,
                               help="Date requested for the biotech to happen")
    owner_user_id = fields.Many2one('res.users', string='Created by User', default=lambda s: s.env.uid)
    category_id = fields.Many2one('biotech.equipment.category', related='equipment_id.category_id', string='Location',
                                  store=True, readonly=True)
    equipment_id = fields.Many2one('biotech.equipment', string='Equipment',
                                   ondelete='restrict', index=True, check_company=True)
    user_id = fields.Many2one('res.users', string='Technician', tracking=True)
    stage_id = fields.Many2one('biotech.stage', string='Stage', ondelete='restrict', tracking=True,
                               group_expand='_read_group_stage_ids', default=_default_stage, copy=False)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    color = fields.Integer('Color Index')
    close_date = fields.Date('Close Date', help="Date the biotech was finished. ")
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
        string='Kanban State', required=True, default='normal', tracking=True)
    # active = fields.Boolean(default=True, help="Set active to false to hide the biotech request without deleting it.")
    archive = fields.Boolean(default=False, help="Set archive to true to hide the biotech request without deleting it.")
    biotech_type = fields.Selection([('corrective', 'Corrective'), ('preventive', 'Preventive')], string='Biotech Type',
                                    default="corrective")
    schedule_date = fields.Datetime('Scheduled Date',
                                    help="Date the biotech team plans the biotech.  It should not differ much from the Request Date. ")
    biotech_team_id = fields.Many2one('biotech.team', string='Team', required=True, default=_get_default_team_id,
                                      check_company=True)
    duration = fields.Float(help="Duration in hours.")
    done = fields.Boolean(related='stage_id.done')

    def archive_equipment_request(self):
        self.write({'archive': True})

    def reset_equipment_request(self):
        """ Reinsert the biotech request into the biotech pipe in the first stage"""
        first_stage_obj = self.env['biotech.stage'].search([], order="sequence asc", limit=1)
        # self.write({'active': True, 'stage_id': first_stage_obj.id})
        self.write({'archive': False, 'stage_id': first_stage_obj.id})

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id and self.biotech_team_id:
            if self.biotech_team_id.company_id and not self.biotech_team_id.company_id.id == self.company_id.id:
                self.biotech_team_id = False

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        if self.equipment_id:
            self.user_id = self.equipment_id.technician_user_id if self.equipment_id.technician_user_id else self.equipment_id.category_id.technician_user_id
            self.category_id = self.equipment_id.category_id
            if self.equipment_id.biotech_team_id:
                self.biotech_team_id = self.equipment_id.biotech_team_id.id

    @api.onchange('category_id')
    def onchange_category_id(self):
        if not self.user_id or not self.equipment_id or (self.user_id and not self.equipment_id.technician_user_id):
            self.user_id = self.category_id.technician_user_id

    @api.model_create_multi
    def create(self, vals_list):
        # context: no_log, because subtype already handle this
        biotech_requests = super().create(vals_list)
        for request in biotech_requests:
            if request.owner_user_id or request.user_id:
                request._add_followers()
            if request.equipment_id and not request.biotech_team_id:
                request.biotech_team_id = request.equipment_id.biotech_team_id
            if request.close_date and not request.stage_id.done:
                request.close_date = False
            if not request.close_date and request.stage_id.done:
                request.close_date = fields.Date.today()
        biotech_requests.activity_update()
        return biotech_requests

    def write(self, vals):
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the Biotech Request changes.
        if vals and 'kanban_state' not in vals and 'stage_id' in vals:
            vals['kanban_state'] = 'normal'
        res = super(BiotechRequest, self).write(vals)
        if vals.get('owner_user_id') or vals.get('user_id'):
            self._add_followers()
        if 'stage_id' in vals:
            self.filtered(lambda m: m.stage_id.done).write({'close_date': fields.Date.today()})
            self.filtered(lambda m: not m.stage_id.done).write({'close_date': False})
            self.activity_feedback(['biotech.mail_act_biotech_request'])
            self.activity_update()
        if vals.get('user_id') or vals.get('schedule_date'):
            self.activity_update()
        if vals.get('equipment_id'):
            # need to change description of activity also so unlink old and create new activity
            self.activity_unlink(['biotech.mail_act_biotech_request'])
            self.activity_update()
        return res

    def activity_update(self):
        """ Update biotech activities based on current record set state.
        It reschedule, unlink or create biotech request activities. """
        self.filtered(lambda request: not request.schedule_date).activity_unlink(['biotech.mail_act_biotech_request'])
        for request in self.filtered(lambda request: request.schedule_date):
            date_dl = fields.Datetime.from_string(request.schedule_date).date()
            updated = request.activity_reschedule(
                ['biotech.mail_act_biotech_request'],
                date_deadline=date_dl,
                new_user_id=request.user_id.id or request.owner_user_id.id or self.env.uid)
            if not updated:
                if request.equipment_id:
                    note = _(
                        'Request planned for %s',
                        request.equipment_id._get_html_link()
                    )
                else:
                    note = False
                request.activity_schedule(
                    'biotech.mail_act_biotech_request',
                    fields.Datetime.from_string(request.schedule_date).date(),
                    note=note, user_id=request.user_id.id or request.owner_user_id.id or self.env.uid)

    def _add_followers(self):
        for request in self:
            partner_ids = (request.owner_user_id.partner_id + request.user_id.partner_id).ids
            request.message_subscribe(partner_ids=partner_ids)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)


class BiotechTeam(models.Model):
    _name = 'biotech.team'
    _description = 'Biotech Teams'

    name = fields.Char('Team Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    member_ids = fields.Many2many(
        'res.users', 'biotech_team_users_rel', string="Team Members",
        domain="[('company_ids', 'in', company_id)]")
    color = fields.Integer("Color Index", default=0)
    request_ids = fields.One2many('biotech.request', 'biotech_team_id', copy=False)
    equipment_ids = fields.One2many('biotech.equipment', 'biotech_team_id', copy=False)

    # For the dashboard only
    todo_request_ids = fields.One2many('biotech.request', string="Requests", copy=False,
                                       compute='_compute_todo_requests')
    todo_request_count = fields.Integer(string="Number of Requests", compute='_compute_todo_requests')
    todo_request_count_date = fields.Integer(string="Number of Requests Scheduled", compute='_compute_todo_requests')
    todo_request_count_high_priority = fields.Integer(string="Number of Requests in High Priority",
                                                      compute='_compute_todo_requests')
    todo_request_count_block = fields.Integer(string="Number of Requests Blocked", compute='_compute_todo_requests')
    todo_request_count_unscheduled = fields.Integer(string="Number of Requests Unscheduled",
                                                    compute='_compute_todo_requests')

    @api.depends('request_ids.stage_id.done')
    def _compute_todo_requests(self):
        for team in self:
            team.todo_request_ids = self.env['biotech.request'].search(
                [('biotech_team_id', '=', team.id), ('stage_id.done', '=', False)])
            team.todo_request_count = len(team.todo_request_ids)
            team.todo_request_count_date = self.env['biotech.request'].search_count(
                [('biotech_team_id', '=', team.id), ('schedule_date', '!=', False)])
            team.todo_request_count_high_priority = self.env['biotech.request'].search_count(
                [('biotech_team_id', '=', team.id), ('priority', '=', '3')])
            team.todo_request_count_block = self.env['biotech.request'].search_count(
                [('biotech_team_id', '=', team.id), ('kanban_state', '=', 'blocked')])
            team.todo_request_count_unscheduled = self.env['biotech.request'].search_count(
                [('biotech_team_id', '=', team.id), ('schedule_date', '=', False)])

    @api.depends('equipment_ids')
    def _compute_equipment(self):
        for team in self:
            team.equipment_count = len(team.equipment_ids)
