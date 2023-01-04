from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError

class SBOpenDemand(models.Model):
    _name='sb.open.demand'
    _inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']
    name=fields.Char('Request No.',default='/',tracking=True)
    client_id=fields.Many2one('res.partner','Client',domain="[('type','=','contact'),('customer_rank','=',1)]")
    project_id=fields.Many2one('project.project','Project',domain="[('partner_id','=',client_id)]")
    worksite_id=fields.Many2one('res.partner','Worksite',domain="[('x_project_id','=',project_id)]")
    street=fields.Char('Street 1',related='worksite_id.street',store=True)
    street2=fields.Char('Street 2',related='worksite_id.street2',store=True)
    country_id=fields.Many2one('res.country','Country',related='worksite_id.country_id',store=True)
    state_id=fields.Many2one('res.country.state',related='worksite_id.state_id',store=True)
    city_id=fields.Many2one('res.city','City',related='worksite_id.city_id',store=True)
    zip=fields.Char('Zip',related='worksite_id.zip',store=True)
    sdm_remarks=fields.Text('SDM/SDE Remarks')
    recruitment_remarks=fields.Text('Recruitment Remarks')
    assigned_date=fields.Date('Assigned Date',tracking=True)
    expected_delivery_date=fields.Date('Target date expected by Delivery Team / Client',tracking=True)
    committed_date=fields.Date('Recruitment / FSM Committed Date',tracking=True)
    state=fields.Selection([('Draft','Draft'),('Active','Active'),('Hold','Hold'),('Fulfilled','Fulfilled'),('Cancelled','Cancelled')],default='Draft',tracking=True)
    resource_type=fields.Selection([('FTE','FTE'),('FTE Backfill','FTE Backfill'),('FTE Backfill','FTE Backfill'),('Dispatch','Dispatch'),('Dispatch Backfill','Dispatch Backfill')],'Resource Type',tracking=True)
    days_per_week=fields.Char('Days per Week',tracking=True)
    owner_ids=fields.Many2many('res.users','demand_owners_rel','demand_id','owner_id',string='Owner Name')
    sdm_ids=fields.Many2many('res.users','demand_sdm_rel','demand_id','sdm_id',string='SDM Name')
    priority=fields.Selection([('Critical','Critical'),('High','High'),('Medium','Medium'),('Low','Low')],'Priority',tracking=True)
    required_quantity=fields.Integer('Required Quantity',tracking=True)
    application_received=fields.Integer('Profiles Received Qty.(FSM & Recr.)',tracking=True,compute='cal_total_applications')
    application_pending=fields.Integer('Pending with Customer',tracking=True,compute='cal_total_applications')
    application_rejected=fields.Integer('Rejected / Backed Out Qty. / Unavailable',tracking=True,compute='cal_total_applications')
    application_selected=fields.Integer('Selected / Onboarded',tracking=True,compute='cal_total_applications')
    balance=fields.Integer('Balance',compute='cal_balance',store=True,tracking=True)
    client_poc_id=fields.Many2one('res.users','Client POC',tracking=True)
    job_description=fields.Text('Job Description')
    language_id=fields.Many2one('res.lang','Language',tracking=True)
    level_id=fields.Many2one('res.lang.level','Level',domain="[('language_id','=',language_id)]",tracking=True)
    target_rate=fields.Float('Target Rate (Vendor only)',tracking=True)
    application_ids=fields.One2many('hr.applicant','demand_id','Application')
    
    @api.depends('application_ids')
    def cal_total_applications(self):
        for each in self:
            pending_applications=0
            rejected_applications=0
            selected_application=0
            for app in each.application_ids:
                if app.stage_id.name=='Second Interview':
                    pending_applications+=1
                elif app.stage_id.name=='Rejected':
                    rejected_applications+=1
                elif app.stage_id.name=='Onboarding':
                    selected_application+=1
            each.application_received=len(each.application_ids)
            each.application_pending=pending_applications
            each.application_rejected=rejected_applications
            each.application_selected=selected_application
            
    @api.depends('required_quantity','application_selected')
    def cal_balance(self):
        for each in self:
            each.balance=each.required_quantity-each.application_selected
    
    def set_active(self):
        self.write({'state':'Active',
                    'name':str(self.id).zfill(6)})
    
    def set_hold(self):
        self.write({'state':'Hold'})
    
    def set_fulfilled(self):
        self.write({'state':'Fulfilled'})
    
    def set_cancel(self):
        self.write({'state':'Cancel'})
        
class Applicant(models.Model):
    _inherit='hr.applicant'
    opportunity_id=fields.Many2one('crm.lead','Opportunity')
    number=fields.Char('Application Number',default='/')
    last_name=fields.Char('Last Name')
    gender=fields.Selection([('Male','Male'),('Female','Female'),('Other','Other')],'Gender')
    date_of_birth=fields.Date('Date of Birth')
    birth_country=fields.Many2one('res.country','Country of Birth')
    birth_state=fields.Many2one('res.country.state','Place of Birth')
    marital_status=fields.Selection([('Single','Single'),('Married','Married'),('Widowed','Widowed'),('Separated','Separated'),('Divorced','Divorced')],'Marital Status')
    applicant_nature=fields.Selection([('Individual','Individual'),('Company','Company')],'Applicant Nature')
    house_no=fields.Char('Flat/House No.')
    street=fields.Char('Street/Society')
    country=fields.Many2one('res.country','Country')
    state=fields.Many2one('res.country.state')
    city=fields.Char('City')
    zip=fields.Integer('Zip')
    customer=fields.Char('Customer',related='opportunity_id.partner_id.name')
    customer_project=fields.Char('Project',related='opportunity_id.project_id.name')
   
    work_rights_copy=fields.Binary('Work Rights Copy')
    work_rights_copy_name=fields.Char('Work Rights Copy')
    
    notice_period=fields.Char('Notice Period')
    
    shortlisted_fte=fields.Selection([('Yes','Yes'),('No','No')],'Available for Full Time?')
    dispatch=fields.Selection([('Yes','Yes'),('No','No')],'Available for Dispatch?')
    part_time=fields.Selection([('Yes','Yes'),('No','No')],'Available for Part Time?')
    work_experience=fields.Integer('Relevant Years of Experience')
    partner=fields.Many2one('hr.employee','Partner',domain="[('type','=','Contractor'),('state','=','Current')]")
    work_rights_status=fields.Selection([('Yes','Yes'),('No','No')],'Work Rights Verified?')
    primary_category=fields.Selection([('Freelancer','Freelancer'),('Student','Student'),('Part Time Work','Part Time Work'),('Full Time','Full Time'),('Service Provider','Service Provider'),('Local Partner','Local Partner'),('Regional Partner','Regional Partner')],'Resource Primary Category')
    cv_review_score=fields.Float('CV Review Score')
    interview_result_score=fields.Float('Interview Result Score')
    
    education_ids=fields.One2many('hr.applicant.education.details','applicant_id','Education')
    experience_ids=fields.One2many('hr.applicant.experience.details','applicant_id','Experience')
    certification_ids=fields.One2many('hr.applicant.certification.details','applicant_id','Certification')
    language_ids=fields.One2many('hr.applicant.languages','applicant_id','Languages')
    requirement_ids=fields.One2many('hr.jobs.requirements.details','applicant_id','Requirements')
    internal_evalaution_ids=fields.One2many('hr.jobs.internal.evaluation.details','applicant_id','Internal Evalaution')
    document_ids=fields.One2many('hr.jobs.documents.details','applicant_id','Documents')
    skyp_id=fields.Char('Skype Contact')
    team_id=fields.Many2one('hr.recruitment.team','Recruitment Team')
    demand_id=fields.Many2one('sb.open.demand','Open Demand')
    show_own_record = fields.Char(string="Own Record", compute='_get_own_applicanttions', search='_search_own_applications')
    def _get_own_applicanttions(self):
        _logger.info("user can show only his record")
        
    def _search_own_applications(self, operator, value):
        user_pool = self.env['res.users']
        user = user_pool.browse(self._uid)
        domain = [('id', '=', -1)]
        if (user.has_group('hr_recruitment.group_hr_recruitment_manager')) or (user.has_group('base.group_erp_manager')):
           return []
        if user.has_group('hr_recruitment.group_hr_recruitment_user'):
            team_obj=self.env.user.x_recruitment_team_id
            application_ids=self.env['hr.applicant'].search([('team_id','=',team_obj.id)]).ids
            domain = [('id', 'in', application_ids)]
        return domain
    
    
    def action_view_employee(self):        
        action = self.env.ref('hr.open_view_employee_list_my').sudo().read()[0]
        query=self.env.cr.execute("""Select id from hr_employee where applicant_id="""+str(self.id))
        result=self.env.cr.fetchall()
        emp_list=[each[0] for each in result]
        action['domain'] = [('id','in',emp_list)]
        return action
    
    @api.model
    def create(self, vals):
        res = super(Applicant, self).create(vals)
        res.number='APP'+str(res.id).zfill(8)
        return res
    
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.display_name
            else:
                if not applicant.partner_name:
                    raise UserError(_('You must define a Contact Name for this applicant.'))
                new_partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile
                })
                applicant.partner_id = new_partner_id
                address_id = new_partner_id.address_get(['contact'])['contact']
            education_list=[(5,0,0)]
            if applicant.education_ids:
                for i in applicant.education_ids:
                    records={
                        'institute_id':i.institute_id.id or False,
                        'degree_id':i.degree_id.id or False,
                        'field_of_study':i.field_of_study.id or False,
                        'start_date':i.start_date or False,
                        'end_date':i.end_date or False,
                        }
                    education_list.append((0,0,records))
            experience_list=[(5,0,0)]
            if applicant.experience_ids:
                for exp in applicant.experience_ids:
                    records={
                        'institute_id':exp.institute_id.id or False,
                        'job_title':exp.job_title or False,
                        'currently_working':exp.currently_working or False,
                        'start_date':exp.start_date or False,
                        'end_date':exp.end_date or False,
                        'description':exp.description or False,
                        'work_experience':exp.work_experience or False,
                        'work_experience_name':exp.work_experience_name or False,
                        }
                    experience_list.append((0,0,records))
            certification_list=[(5,0,0)]
            if applicant.certification_ids:
                for k in applicant.certification_ids:
                    records={
                        'type':k.type or False,
                        'title':k.title.id or False,
                        'number':k.number or False,
                        'issue_date':k.issue_date or False,
                        'expiry_date':k.expiry_date or False,
                        'limited_license':k.limited_license or False,
                        }
                    certification_list.append((0,0,records))
            
            language_list=[(5,0,0)]
            if applicant.language_ids:
                for l in applicant.language_ids:
                    records={
                        'language_id':l.language_id.id or False,
                        'level_id':l.level_id.id or False,
                        'is_native':l.is_native or False
                        }
                    language_list.append((0,0,records))
            
            requirement_list=[(5,0,0)]
            if applicant.requirement_ids:
                for m in applicant.requirement_ids:
                    records={
                        'sequence':m.sequence or False,
                        'skill_type':m.skill_type or False,
                        'skill_id':m.skill_id.id or False,
                        'level':m.level or False,
                        'availablity':m.availablity or False
                        }
                    requirement_list.append((0,0,records))
            
            internal_evaluation_list=[(5,0,0)]
            if applicant.internal_evalaution_ids:
                for n in applicant.internal_evalaution_ids:
                    records={
                        'sequence':n.sequence or False,
                        'internal_evaluation_id':n.internal_evaluation_id.id or False,
                        'level':n.level or False,
                        }
                    internal_evaluation_list.append((0,0,records))
            
            document_list=[(5,0,0)]
            if applicant.document_ids:
                for o in applicant.document_ids:
                    records={
                        'sequence':o.sequence or False,
                        'document_id':o.document_id.id or False,
                        'attachment':o.attachment or False,
                        'attachment_name':o.attachment_name or False,
                        }
                    document_list.append((0,0,records))
                    
            if applicant.partner_name or contact_name:
                employee_data = {
                    'default_name': applicant.partner_name or contact_name,
                    'default_partner_name':self.partner_name  or contact_name,
                    'default_last_name':self.last_name,
                    'default_gender':applicant.gender.lower(),
                    'default_birthday':applicant.date_of_birth,
                    'default_country_of_birth':applicant.birth_country.id,
#                     'default_place_of_birth':applicant.birth_state.name,
                    'default_marital_status':applicant.marital_status,
                    'default_applicant_nature':applicant.applicant_nature,
                    'default_categ_ids':applicant.categ_ids.ids,
                    'default_recruiter_id':applicant.user_id.id,
                    'default_recruiter_id':applicant.user_id.id,
                    'default_work_email': applicant.email_from,
                    'default_work_phone': applicant.partner_phone,
                    'default_mobile_phone': applicant.partner_mobile,
                    'default_skyp_id': applicant.skyp_id,
                    'default_degree_id': applicant.type_id.id,
                    'default_priority': applicant.priority,
                    'default_medium_id': applicant.medium_id.id,
                    'default_source_id': applicant.source_id.id,
                    'default_house_no': applicant.house_no,
                    'default_country': applicant.country.id,
                    'default_city': applicant.city,
                    'default_street': applicant.street,
                    'default_state_id': applicant.state.id,
                    'default_zip': applicant.zip,
                    'default_applied_job_id': applicant.job_id.id,
                    'default_opportunity_id': applicant.opportunity_id.id,
                    'default_customer': applicant.customer,
                    'default_customer_project': applicant.customer_project,
                    'default_department_id': applicant.department_id.id,
                    'default_salary_expected': applicant.salary_expected,
                    'default_salary_expected_extra': applicant.salary_expected_extra,
                    'default_salary_proposed': applicant.salary_proposed,
                    'default_salary_proposed_extra': applicant.salary_proposed_extra,
                    'default_availability': applicant.availability,
                    'default_notice_period': applicant.notice_period,
                    'default_shortlisted_fte': applicant.shortlisted_fte,
                    'default_dispatch': applicant.dispatch,
                    'default_part_time': applicant.part_time,
                    'default_cv_review_score': applicant.cv_review_score,
                    'default_interview_result_score': applicant.interview_result_score,
                    'default_partner': applicant.partner.id,
                    'default_experience':applicant.work_experience,
                    'default_work_rights_status': applicant.work_rights_status,
                    'default_primary_category': applicant.primary_category,
                    'default_application_summary': applicant.description,
 
                    'default_job_id': applicant.job_id.id,
                    'default_job_title': applicant.job_id.name,
                    'address_home_id': address_id,
                    'default_address_id': applicant.company_id and applicant.company_id.partner_id
                            and applicant.company_id.partner_id.id or False,
                    'form_view_initial_mode': 'edit',
                    'default_applicant_id': applicant.id,
                    'default_education_ids':education_list or [],
                    'default_experience_ids':experience_list or [],
                    'default_certification_ids':certification_list or [],
                    'default_language_ids':language_list or [],
                    'default_requirement_ids':requirement_list or [],
                    'default_internal_evalaution_ids':internal_evaluation_list or [],
                    'default_document_ids':document_list or [],
                    
                    }
                    
        dict_act_window = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        dict_act_window['context'] = employee_data
        return dict_act_window
    
class HrJobsRequirementDetails(models.Model):
    _name='hr.jobs.requirements.details'
    skill_id=fields.Many2one('hr.jobs.requirements','Skill')
    skill_type=fields.Selection([('Skillset','Skillset'),('Equipment','Equipment')],'Type',related='skill_id.type')
    sequence=fields.Integer('Sequence',related='skill_id.sequence')
    level=fields.Selection([('Poor','Poor'),('Fair','Fair'),('Below Average','Below Average'),('Average','Average'),('Above Average','Average'),('Fairly Good','Fairly Good'),('Good','Good'),('Very Good','Very Good'),('Excellent','Excellent')],'Level')
    availablity=fields.Selection([('Yes','Yes'),('No','No')],'Availabilty')
    applicant_id=fields.Many2one('hr.applicant','Application')
    employee_id=fields.Many2one('hr.employee','Employee')
    task_id=fields.Many2one('project.task','Task')
    
class InternalEvaluationDetails(models.Model):
    _name='hr.jobs.internal.evaluation.details'
    internal_evaluation_id=fields.Many2one('hr.jobs.internal.evaluation','Internal Evalaution')
    sequence=fields.Integer('Sequence',related='internal_evaluation_id.sequence')
    level=fields.Selection([('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')],'Level')
    applicant_id=fields.Many2one('hr.applicant','Application')
    employee_id=fields.Many2one('hr.employee','Employee')
    
class ApplicantLanguageDetails(models.Model):
    _name='hr.applicant.languages'
    language_id=fields.Many2one('res.lang','Language',required=True)
    level_id=fields.Many2one('res.lang.level','Level',required=True,domain="[('language_id','=',language_id)]")
    is_native=fields.Boolean('Is Native Language?')
    applicant_id=fields.Many2one('hr.applicant','Application')
    employee_id=fields.Many2one('hr.employee','Employee')
    
class ApplicantDocuementDetails(models.Model):
    _name='hr.jobs.documents.details'
    document_id=fields.Many2one('hr.jobs.documents','Documents')
    sequence=fields.Integer('Sequence',related='document_id.sequence')
    attachment=fields.Binary('Attachment')
    attachment_name=fields.Char('Attachment')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    employee_id=fields.Many2one('hr.employee','Employee')
    
class ApplicantEducationDetails(models.Model):
    _name='hr.applicant.education.details'
    institute_id=fields.Many2one('hr.institute','Institute',required=True)
    degree_id=fields.Many2one('hr.recruitment.degree','Degree',required=True)
    field_of_study=fields.Many2one('hr.recruitment.specialization','Field of Study')
    start_date=fields.Date('Start Date')
    end_date=fields.Date('End Date')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    employee_id=fields.Many2one('hr.employee','Employee')
    approx_date=fields.Boolean('Approx. Date',default=False)
    
class ApplicantExperienceDetails(models.Model):
    _name='hr.applicant.experience.details'
    institute_id=fields.Many2one('hr.institute','Organization',required=True)
    job_title=fields.Char('Job Title',required=True)
    currently_working=fields.Boolean('Currently Working')
    start_date=fields.Date('Start Date')
    end_date=fields.Date('End Date')
    description=fields.Text('Description')
    work_experience=fields.Binary('Attachment')
    work_experience_name=fields.Char('Attachment')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    employee_id=fields.Many2one('hr.employee','Employee')
    approx_date=fields.Boolean('Approx. Date',default=False)
    
class ApplicantCertificationDetails(models.Model):
    _name='hr.applicant.certification.details'
    type=fields.Selection([('Certificate','Certificate'),('License','License')],'Type',required=True)
    title=fields.Many2one('hr.certification','Title',required=True)
    number=fields.Char('Number',required=True)
    issue_date=fields.Date('Date Issue')
    expiry_date=fields.Date('Expiry Date')
    limited_license=fields.Char('If the license limited to a specific geographic area? Explain (optional)')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    employee_id=fields.Many2one('hr.employee','Employee')
    approx_date=fields.Boolean('Approx. Date',default=False)
    
class HrInstitute(models.Model):
    _name='hr.institute'
    name=fields.Char('Name')

class HrRecruitmentSpecialization(models.Model):
    _name='hr.recruitment.specialization'
    name=fields.Char('Name')

class HrCertification(models.Model):
    _name='hr.certification'
    name=fields.Char('Name')
    
class hr_job(models.Model):
    _inherit = 'hr.job'
    requirements_ids = fields.Many2many('hr.jobs.requirements','jobs_requirement_rel','jobs_id','requirement_id',"Requirements")
    product_id=fields.Many2one('product.template','Product',ondelete='restrict')
    show_own_record = fields.Char(string="Own Record", compute='_get_own_jobs', search='_search_own_jobs')
    def _get_own_jobs(self):
        _logger.info("user can show only his record")
        
    def _search_own_jobs(self, operator, value):
        user_pool = self.env['res.users']
        user = user_pool.browse(self._uid)
        domain = [('id', '=', -1)]
        if (user.has_group('hr_recruitment.group_hr_recruitment_manager')) or (user.has_group('base.group_erp_manager')):
           return []
        if user.has_group('hr_recruitment.group_hr_recruitment_user'):
            team_obj=self.env.user.x_recruitment_team_id
            applicant_obj=self.env['hr.applicant'].search([('team_id','=',team_obj.id)])
            job_list=[]
            for each in applicant_obj:
                job_list.append(each.job_id.id)
            domain = [('id', 'in', job_list)]
        return domain
    
    def _compute_application_count(self):
        team_obj=self.env.user.x_recruitment_team_id
#         applicant_obj=self.env['hr.applicant'].search([('team_id','=',team_obj.id),('job_id','=',self.id)])
#         read_group_result = self.env['hr.applicant'].read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
#         result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            applicant_obj=self.env['hr.applicant'].search([('team_id','=',team_obj.id),('job_id','=',job.id)])
            job.application_count = len(applicant_obj)
    @api.model
    def create(self, vals):
        res = super(hr_job, self).create(vals)
        product_obj=self.env['product.template'].search([('name','=',res.name)])
        income_account_obj = self.env.ref('l10n_generic_coa.1_income')
        expense_account_obj = self.env.ref('l10n_generic_coa.1_expense_invest')
        uom_obj=self.env.ref('uom.product_uom_day')
        if not product_obj:
            product_vals={'name':res.name,
                          'sale_ok':True,
                          'purchase_ok':True,
                          'type':'service',
                          'service_policy':'delivered_timesheet',
                          'service_tracking':'task_in_project',
                          'property_account_income_id':income_account_obj.id,
                          'property_account_expense_id':expense_account_obj.id,
                          'supplier_taxes_id':None,
                          'taxes_id':None,
                          'uom_id':uom_obj.id,
                          'uom_po_id':uom_obj.id
                          }
            product_obj=self.env['product.template'].create(product_vals)
            res.write({'product_id':product_obj.id})
        return res
    
class ResLangLevel(models.Model):
    _name='res.lang.level'
    name=fields.Char('Level',required=True)
    language_id=fields.Many2one('res.lang','Language')

class ResLang(models.Model):
    _inherit='res.lang'
    lang_level_ids=fields.One2many('res.lang.level','language_id','Language Level')

class ResUsers(models.Model):
    _inherit = 'res.users'

    x_recruitment_team_id= fields.Many2one(
        'hr.recruitment.team', "User's Recruitment Team")


class HrRecruitmentTeam(models.Model):
    _name = 'hr.recruitment.team'
    _description = 'Recruitment Team'
    _inherit = ['mail.thread']
    _order = "sequence"
    _check_company_auto = True
    
    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]
    
    name=fields.Char('Recruitment Team')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the Sales Team without removing it.")
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Team Leader', check_company=True)
    # memberships
    member_ids = fields.One2many(
        'res.users', 'x_recruitment_team_id', string='Channel Members',
        check_company=True, domain=[('share', '=', False)],
        help="Add members to automatically assign their documents to this sales team. You can only be member of one team.")
    # UX options
    color = fields.Integer(string='Color Index', help="The color of the channel")
    favorite_user_ids = fields.Many2many(
        'res.users', 'recruitment_team_user_rel', 'team_id', 'user_id',
        string='Favorite Members', default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard', compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')
    dashboard_graph_data = fields.Text(compute='_compute_dashboard_graph')
    
    @api.model
    def create(self, values):
        team = super(HrRecruitmentTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
        if values.get('member_ids'):
            team._add_members_to_favorites()
        return team
 
    def write(self, values):
        res = super(HrRecruitmentTeam, self).write(values)
        if values.get('member_ids'):
            self._add_members_to_favorites()
        return res
     
    def _compute_is_favorite(self):
        for team in self:
            team.is_favorite = self.env.user in team.favorite_user_ids

    def _inverse_is_favorite(self):
        sudoed_self = self.sudo()
        to_fav = sudoed_self.filtered(lambda team: self.env.user not in team.favorite_user_ids)
        to_fav.write({'favorite_user_ids': [(4, self.env.uid)]})
        (sudoed_self - to_fav).write({'favorite_user_ids': [(3, self.env.uid)]})
        return True
    
    def _add_members_to_favorites(self):
        for team in self:
            team.favorite_user_ids = [(4, member.id) for member in team.member_ids]