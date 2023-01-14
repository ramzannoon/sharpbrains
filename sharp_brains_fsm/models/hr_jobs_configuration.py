from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError
from timezonefinder import TimezoneFinder
from datetime import datetime
from pytz import timezone, utc




class hr_jobs_requirements(models.Model):
    _name = 'hr.jobs.requirements'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char('Name',compute = "_type_skill",tracking=True)
    sequence= fields.Integer('Sequence',tracking=True)
    type = fields.Selection([('Skillset','Skillset'),('Equipment','Equipment')],'Type',tracking=True)
    category= fields.Char('Category',tracking=True)
    skill= fields.Char('Skill',tracking=True)

#     @api.constrains('sequence')
#     def _check_seq(self):
#         for each in self: 
#             jobs_obj = self.env['hr.jobs.requirements'].search([('sequence','=',each.sequence)])
#             if len(jobs_obj) > 1:
#                 raise ValidationError(('This %s Number already exist! ')%(each.sequence))
#     
#     @api.constrains('category')
#     def _check_category(self):
#         for each in self: 
#             jobs_obj = self.env['hr.jobs.requirements'].search([('category','=',each.category)])
#             if len(jobs_obj) > 1:
#                 raise ValidationError(('This %s Category already exist! ')%(each.category))
#     
#     @api.constrains('skill')
#     def _check_skill(self):
#         for each in self: 
#             jobs_obj = self.env['hr.jobs.requirements'].search([('skill','=',each.skill)])
#             if len(jobs_obj) > 1:
#                 raise ValidationError(('This %s Skill already exist! ')%(each.skill))
#     
#     
    @api.depends('type','skill')
    def _type_skill(self):
        for each in self:
            each.name
            if each.type and each.skill:
                can = str(each.type)+" - "+str(each.skill) 
                each.name = can
            else:
                each.name

class hr_jobs_internal_evaluation(models.Model):
    _name = 'hr.jobs.internal.evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    _rec_name='internal_evalaution'                   
    sequence= fields.Integer('Sequence',tracking=True)           
    internal_evalaution= fields.Char('Internal Evaluation',tracking=True)

    @api.constrains('sequence')
    def _check_seq(self):
        for each in self: 
            jobs_obj = self.env['hr.jobs.internal.evaluation'].search([('sequence','=',each.sequence)])
            if len(jobs_obj) > 1:
                raise ValidationError(('This %s Number already exist! ')%(each.sequence))
    
    @api.constrains('internal_evalaution')
    def _check_internal_evalaution(self):
        for each in self: 
            jobs_obj = self.env['hr.jobs.internal.evaluation'].search([('internal_evalaution','=',each.internal_evalaution)])
            if len(jobs_obj) > 1:
                raise ValidationError(('This %s Internal Evalaution already exist! ')%(each.internal_evalaution))

class hr_jobs_documents(models.Model):
    _name = 'hr.jobs.documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name='dcouments'                
    sequence= fields.Integer('Sequence',tracking=True)           
    dcouments= fields.Char('Dcouments',tracking=True)
    
    
    
    
     
    @api.constrains('sequence')
    def _check_seq(self):
        for each in self: 
            jobs_obj = self.env['hr.jobs.documents'].search([('sequence','=',each.sequence)])
            if len(jobs_obj) > 1:
                raise ValidationError(('This %s Number already exist! ')%(each.sequence))
     
    @api.constrains('dcouments')
    def _check_dcouments(self):
        for each in self: 
            jobs_obj = self.env['hr.jobs.documents'].search([('dcouments','=',each.dcouments)])
            if len(jobs_obj) > 1:
                raise ValidationError(('This %s Dcouments already exist! ')%(each.dcouments))
# class ResStates(models.Model):
#     _inherit='res.country.state'
#     territory_id=fields.Many2one('sb.territory','Territory')
#  
class ResCountry(models.Model):
    _inherit='res.country'
    x_region=fields.Selection([('APAC','APAC'),('EMEA','EMEA')],'Region')
     
class City(models.Model):
    _name='res.city'
    name=fields.Char('City/Territory',required=True)
    state_id=fields.Many2one('res.country.state','State',required=True,domain="[('country_id','=',country_id)]")
    country_id=fields.Many2one('res.country','Country',required=True)
    primary_assignment_id=fields.Many2one('hr.employee','Primary Assignment',domain="[('state','=','Current'),('employee_type','=','Field Service Engineer(Individual)')]")
    employee_ids=fields.Many2many('hr.employee',string='Field Service Workers',domain="[('state','=','Current'),('employee_type','=','Employee')]")
    backfill_engineer_id=fields.Many2one('hr.employee','Back fill Engineer')
    secondary_backfill_id=fields.Many2one('hr.employee','Secondary Back fill Engineer')
    worksites_count = fields.Integer('Worksites Count', compute="_compute_worksites_count")
    
    def _compute_worksites_count(self):
        for each in self:
            if type(each.id) is int:
                each.worksites_count=0
                query=self.env.cr.execute("""Select id from res_partner where type='work_site' and city_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.worksites_count=len(result)
            else:
                each.worksites_count=0
    
    def action_view_work_sites(self):        
        action = self.env.ref('sharp_brains.action_partner_worksites').sudo().read()[0]

        query=self.env.cr.execute("""Select id from res_partner where type='work_site' and city_id="""+str(self.id))
        result=self.env.cr.fetchall()
        worksite_list=[each[0] for each in result]
        action['domain'] = [('id','in',worksite_list)]
        return action
# class Territory(models.Model):
#     _name='sb.territory'
#     name=fields.Char('Name',required=True)
#     code=fields.Char('Code')
#     primary_assignment_id=fields.Many2one('hr.employee','Primary Assignment')
#     description=fields.Text('Description')
#     employee_ids=fields.Many2many('hr.employee',string='Field Service Workers')
#     type = fields.Selection([('zip', 'Zip'),
#                              ('state', 'State'),
#                              ('country', 'Country')], 'Type')
#   
#     zip_codes = fields.Char(string='ZIP Codes')
#     state_ids = fields.One2many('res.country.state',
#                                 'territory_id', string='State Names')
#     country_ids = fields.One2many('res.country',
#                                   'territory_id',
#                                   string='Country Names')
# # class ResPartner(models.Model):
# #     _inherit='res.partner'
# #     fsm_location = fields.Boolean('Is a FS Location')
#      
class SBLocation(models.Model):
    _name = 'sb.location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Field Service Location'
       
    ref = fields.Char(string='Internal Reference', copy=False)
    direction = fields.Char(string='Directions')
    partner_id = fields.Many2one('res.partner', string='Related Partner',
                                 required=True, ondelete='restrict',
                                 delegate=True, auto_join=True)
    owner_id = fields.Many2one('res.partner', string='Client',
                               required=True, ondelete='restrict',
                               auto_join=True)
    end_customer = fields.Many2one('res.partner', string='End Customer',
                                 domain="[('is_company', '=', True),('fsm_location','=',False)]",
                                 index=True)
    contact_id = fields.Many2one('res.partner', string='Primary Contact',
                                 domain="[('is_company', '=', False),('fsm_location','=',False)]",
                                 index=True)
    site_contact_name = fields.Char(string='Site POC')
    description = fields.Char(string='Description')
    territory_id = fields.Many2one('sb.territory', string='Territory')
#     branch_id = fields.Many2one('sb.branch', string='Branch')
#     district_id = fields.Many2one('sb.district', string='District')
#     region_id = fields.Many2one('sb.region', string='Region')
    territory_manager_id = fields.Many2one(string='Primary Assignment',
                                           )
#     district_manager_id = fields.Many2one(string='District Manager',
#                                           related='district_id.partner_id')
#     region_manager_id = fields.Many2one(string='Region Manager',
#                                         related='region_id.partner_id')
#     branch_manager_id = fields.Many2one(string='Branch Manager',
#                                         related='branch_id.partner_id')
   
    calendar_id = fields.Many2one('resource.calendar',
                                  string='Office Hours')
    fsm_parent_id = fields.Many2one('sb.location', string='Parent',
                                    index=True)
    notes = fields.Text(string="Location Notes")
   
    contact_count = fields.Integer(string='Contacts Count',
                                    compute='_compute_contact_ids')
#     equipment_count = fields.Integer(string='Equipment',
#                                      compute='_compute_equipment_ids')
#     sublocation_count = fields.Integer(string='Sub Locations',
#                                        compute='_compute_sublocation_ids')
    complete_name = fields.Char(string='Complete Name',
                                compute='_compute_complete_name',
                                store=True)
#     complete_name = fields.Char(string='Complete Name')
#     hide = fields.Boolean(default=False)
#     stage_id = fields.Many2one('sb.stage', string='Stage',
#                                track_visibility='onchange',
#                                index=True, copy=False,
#                                group_expand='_read_group_stage_ids',
#                                default=lambda self: self._default_stage_id())
#     fsm_location=fields.Boolean(default=True)
    tz = fields.Char(string='Timezone', compute='_compute_tz')
#     tz = fields.Char(string='Timezone')
#       
#     @api.constrains('fsm_parent_id')
#     def _check_location_recursion(self):
#         if not self._check_recursion(parent='fsm_parent_id'):
#             raise ValidationError(_('You cannot create recursive location.'))
#         return True
#       
#     @api.onchange('country_id')
#     def _onchange_country_id(self):
#         if self.country_id and self.country_id != self.state_id.country_id:
#             self.state_id = False
#               
#     @api.onchange('state_id')
#     def _onchange_state(self):
#         if self.state_id.country_id:
#             self.country_id = self.state_id.country_id
#               
#     @api.onchange('fsm_parent_id')
#     def _onchange_fsm_parent_id(self):
#         self.owner_id = self.fsm_parent_id.owner_id or False
#         self.contact_id = self.fsm_parent_id.contact_id or False
#         self.direction = self.fsm_parent_id.direction or False
#         self.street = self.fsm_parent_id.street or False
#         self.street2 = self.fsm_parent_id.street2 or False
#         self.city = self.fsm_parent_id.city or False
#         self.zip = self.fsm_parent_id.zip or False
#         self.state_id = self.fsm_parent_id.state_id or False
#         self.country_id = self.fsm_parent_id.country_id or False
#         self.tz = self.fsm_parent_id.tz or False
# #         self.territory_id = self.fsm_parent_id.territory_id or False
#           
#     def name_get(self):
#         results = []
#         for rec in self:
#             results.append((rec.id, rec.complete_name))
#         return results
#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=100):
#         args = args or []
#         recs = self.browse()
#         if name:
#             recs = self.search([('ref', 'ilike', name)] + args, limit=limit)
#         if not recs:
#             recs = self.search([('name', operator, name)] + args, limit=limit)
#         return recs.name_get()
#   
#   
#     def _compute_tz(self):
#         tf = TimezoneFinder()
#         for rec in self:
#             tz = tf.timezone_at(lng=rec.partner_longitude, lat=rec.partner_latitude) # returns timezone e.g 'Europe/Berlin'
#             rec.tz = tz
# # 
#     @api.depends('partner_id')
#     def _compute_tz(self):
#         tf = TimezoneFinder()
#         for rec in self:
#             tz = tf.timezone_at(lng=rec.partner_longitude, lat=rec.partner_latitude) # returns timezone e.g 'Europe/Berlin'
#             rec.tz = tz
#     @api.depends('partner_id.name', 'fsm_parent_id.complete_name', 'ref')
#     def _compute_complete_name(self):
#         for loc in self:
#             if loc.fsm_parent_id:
#                 if loc.ref:
#                     loc.complete_name = '%s / [%s] %s' % (
#                         loc.fsm_parent_id.complete_name, loc.ref,
#                         loc.partner_id.name)
#                 else:
#                     loc.complete_name = '%s / %s' % (
#                         loc.fsm_parent_id.complete_name, loc.partner_id.name)
#             else:
#                 if loc.ref:
#                     loc.complete_name = '[%s] %s' % (loc.ref,
#                                                      loc.partner_id.name)
#                 else:
#                     loc.complete_name = loc.partner_id.name
#       
#       
#     @api.model
#     def create(self, vals):
#         vals.update({'fsm_location': True})
#         return super(SBLocation, self).create(vals)
#       
#     def write(self,vals):
#         if ('country_id' in vals) or ('city' in vals) or ('state_id' in vals) or ('street' in vals):
#             for loc in self:
#                 if loc.partner_id:
#                     loc.partner_id.geo_localize()
#                 vals['partner_latitude'] = loc.partner_latitude
#                 vals['partner_longitude'] = loc.partner_longitude
#         return super(SBLocation, self).write(vals)
    