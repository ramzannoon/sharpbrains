from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError
from timezonefinder import TimezoneFinder
 
class ResContactDetails(models.Model):
    _name='res.partner.contact.details'
    type=fields.Selection([('Primary','Primary'),('Secondary','Secondary'),('Tertiary','Tertiary')],'Type')
    name=fields.Char('Name')
    phone=fields.Char('Contact 1')
    mobile=fields.Char('Contact 2')
    email=fields.Char('Email')
    partner_id=fields.Many2one('res.partner','Partner')


class AssignedWorkersDetails(models.Model):
    _name='assigned.worker.details'
    type=fields.Selection([('Primary','Primary'),('Back fill','Back fill'),('Secondary Back fill','Secondary Back fill')],'Type')
    employee_id=fields.Many2one('hr.employee','Name',domain="[('state','=','Current'),('employee_type','in',['Employee','Field Service Engineer(Individual)'])]")
    phone=fields.Char('Phone',related="employee_id.work_phone")
    email=fields.Char('Email',related='employee_id.work_email')
    partner_id=fields.Many2one('res.partner','Partner')
    
class res_partner(models.Model):
    _inherit = 'res.partner'


    project_details_ids= fields.One2many('project.details','partner_id','Project Details')
    pc= fields.Char('PC')
    sdm= fields.Char('SDM')
    client_sdm= fields.Char('Client SDM')
    fsm_location = fields.Boolean('Is a FS Location?')
    fsm_worker = fields.Boolean('Is a FS Engineer?')
    fsm_partner = fields.Boolean('Is a FS Partner?')
    internal_employee=fields.Boolean('Is Internal Employee?')
    city_id=fields.Many2one('res.city','City')
    city=fields.Char('City',related='city_id.name',store=True)
    type = fields.Selection(
        [('end_customer','End Customer'),
         ('work_site','Work Site'),
         ('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
        ], string='Work Site',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")
    site_poc = fields.Char(string='Site POC')
    tz = fields.Char(string='Timezone', compute='_compute_tz')
    calendar_id = fields.Many2one('resource.calendar',
                                  string='Office Hours')
    instruction = fields.Text(string="Site Instructions")
    assigned_worker_id=fields.Many2one('hr.employee','Primary Engineer',domain="[('state','=','Current'),('employee_type','=','Field Service Engineer(Individual)')]")
    backfill_engineer_id=fields.Many2one('hr.employee','Back fill Engineer',domain="[('state','=','Current'),('employee_type','=','Field Service Engineer(Individual)')]")
    secondary_backfill_id=fields.Many2one('hr.employee','Secondary Back fill Engineer',domain="[('state','=','Current'),('employee_type','=','Field Service Engineer(Individual)')]")
    x_project_id=fields.Many2one('project.project','Project',domain="[('partner_id','=',parent_id)]")
    x_end_customer_id=fields.Many2one('res.partner',domain="[('customer_rank','!=',0),('type','=','end_customer'),('parent_id','=',parent_id)]")
    x_contact_name_1=fields.Char('Name')
    
    x_contact_name_2=fields.Char('Name')
    x_phone_2=fields.Char('Contact 1')
    x_mobile_2=fields.Char('Contact 2')
    x_email_2=fields.Char('Email')
    x_contact_name_3=fields.Char('Name')
    x_phone_3=fields.Char('Contact 1')
    x_mobile_3=fields.Char('Contact 2')
    x_email_3=fields.Char('Email')
    contact_detail_ids=fields.One2many('res.partner.contact.details','partner_id','Contact Details')
    assigned_workers_ids=fields.One2many('assigned.worker.details','partner_id','Assigned Workers')
    x_region=fields.Selection([('APAC','APAC'),('EMEA','EMEA')],'Region',related='country_id.x_region',store=True)
#     @api.onchange('country_id')
#     def _onchange_country(self):
#         if self.country_id:
#             self.state_id = False
#             self.city_id = False
# 
#    
#     def _get_contact_name(self, partner, name):
#         super(res_partner,self)._get_contact_name(partner, name)
#         return "%s" % (name)
#     
    def cal_display_name(self):
        diff = dict(show_address=None, show_address_only=None, show_email=None, html_format=None, show_vat=None)
        names = dict(self.with_context(**diff).name_get())
        partner_obj=self.env['res.partner'].search([('type','!=','contact')])
        for partner in partner_obj:
            partner.display_name = partner.name
    @api.depends('name')
    def name_get(self):
        result = []
        for rec in self:
            name = str(rec.name)
            result.append((rec.id, name))
        return result
    
    @api.depends('partner_longitude','partner_latitude')
    def _compute_tz(self):
        tf = TimezoneFinder()
        for rec in self:
            tz = tf.timezone_at(lng=rec.partner_longitude, lat=rec.partner_latitude) # returns timezone e.g 'Europe/Berlin'
            rec.tz = tz
#     fsm_person = fields.Boolean('Is a FS Worker')
    
    @api.model
    def create(self,vals):
        partner=super(res_partner, self).create(vals)
        partner.geo_localize()
        return partner
    
    @api.onchange('x_project_id','city_id','country_id')
    def cal_name(self):
        for each in self:
            if each.x_project_id and each.city_id and each.country_id and each.type=='worksite':
                each.write({'name':str(each.x_project_id.name)+" - "+str(each.city_id.name)+" - "+str(each.country_id.name)})
    @api.model
    def create(self,vals):
        project_id=None
        city_id=None
        country_id=None
        type=None
        if vals.get('type',False):
            type=vals.get('type',False)
        if vals.get('x_project_id',False):
            id=vals.get('x_project_id',False)
            project_id=self.env['project.project'].search([('id','=',id)])
        if vals.get('city_id',False):
            id=vals.get('city_id',False)
            city_id=self.env['res.city'].search([('id','=',id)])
        if vals.get('country_id',False):
            id=vals.get('country_id',False)
            country_id=self.env['res.country'].search([('id','=',id)])
        if type=='work_site':
            if project_id and city_id and country_id :
                vals.update({'name':str(project_id.name)+" - "+str(city_id.name)+" - "+str(country_id.name)
                                })
           
        return super(res_partner,self).create(vals)
    
    def write(self,vals):
        project_id=self.x_project_id
        city_id=self.city_id
        country_id=self.country_id
        if vals.get('x_project_id',False):
            id=vals.get('x_project_id',False)
            project_id=self.env['project.project'].search([('id','=',id)])
        if vals.get('city_id',False):
            id=vals.get('city_id',False)
            city_id=self.env['res.city'].search([('id','=',id)])
        if vals.get('country_id',False):
            id=vals.get('country_id',False)
            country_id=self.env['res.country'].search([('id','=',id)])
        if project_id and city_id and country_id and self.type=='work_site':
            vals.update({'name':str(project_id.name)+" - "+str(city_id.name)+" - "+str(country_id.name)
                            })
           
        return super(res_partner,self).write(vals)
        
        
        
        
class project_details(models.Model):
    _name = 'project.details'
     
    partner_id = fields.Many2one('res.partner','Partner ID', ondelete='restrict')
     
     
    project_id = fields.Many2one('partner.projects','Project',ondelete='restrict')
    job_id = fields.Many2one('hr.jobs', 'Job',ondelete='restrict')
    
    
    
    
class partner_projects(models.Model): 
    _name = 'partner.projects'
     
    name = fields.Char('Name')
     
     
    @api.constrains('name')
    def _check_seq(self):
        for each in self: 
            partner_project_obj = self.env['partner.projects'].search([('name','=',each.name)])
            if len(partner_project_obj) > 1:
                raise ValidationError(('This %s Name already exist! ')%(each.name))
    