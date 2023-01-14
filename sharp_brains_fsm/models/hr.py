from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError


class HREmployeePublic(models.Model):
    _inherit = "hr.employee.public"
    state=fields.Selection([('Draft','Draft'),('Current','Current'),('Former','Former')],'State',default='Draft',store=True)
    employee_type=fields.Selection([('Employee','Employee'),('Field Service Engineer(Individual)','Field Service Engineer(Individual)'),('Field Service Engineer(Company)','Field Service Engineer(Company)')],'Employee Type')
#     no_depend=fields.Boolean('no depend')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    day_rate=fields.Float('Day Rate', digits=(12,1))
    hourly_rate=fields.Float('Hourly Rate', digits=(12,1))
    dispatch_half_day_rate=fields.Float('Half Day Rate', digits=(12,1))
    dispatch_monthly_rate=fields.Float('Monthly Rate', digits=(12,1))
    dispatch_ooh_uplift_from=fields.Float('OOH Uplift From' , digits=(12,1))
    dispatch_ooh_uplift_to=fields.Float('OOH Uplift To', digits=(12,1))
    dispatch_weekend_uplift_from=fields.Float('Weekend/Public Holidays Uplift From', digits=(12,1))
    dispatch_weekend_uplift_to=fields.Float('Weekend/Public Holidays Uplift To', digits=(12,1))
    dispatch_milage=fields.Float('Milage(per km)', digits=(12,1))
    fte_day_rate=fields.Float('Day Rate', digits=(12,1))
    fte_hourly_rate=fields.Float('Hourly Rate', digits=(12,1))
    fte_half_day_rate=fields.Float('Half Day Rate', digits=(12,1))
    fte_monthly_rate=fields.Float('Monthly Rate', digits=(12,1))
    fte_ooh_uplift_from=fields.Float('OOH Uplift From', digits=(12,1))
    fte_ooh_uplift_to=fields.Float('OOH Uplift To', digits=(12,1))
    fte_weekend_uplift_from=fields.Float('Weekend/Public Holidays Uplift From', digits=(12,1))
    fte_weekend_uplift_to=fields.Float('Weekend/Public Holidays Uplift To', digits=(12,1))
    fte_milage=fields.Float('Milage(per km)', digits=(12,1))
    experience=fields.Float('Experience')
#     work_right=fields.Binary('Work Rights Copy')
    work_right_name=fields.Char('Work Rights Name')
    work_right_verified=fields.Boolean('Work Right Verified')
    notice_period=fields.Integer('Notice Period')
    vendor_id=fields.Many2one('res.partner','Vendor/Sub Contractor')
    shortlist_fte=fields.Boolean('Shortlist for FTE')
    
    local_language_level=fields.Selection([('A1','A1'),('A2','A2'),('B1','B1'),('B2','B2'),('C1','C1'),('C2','C2')],'Local Language Level')
    english_language_level=fields.Selection([('A1','A1'),('A2','A2'),('B1','B1'),('B2','B2'),('C1','C1'),('C2','C2')],'English Language Level')
    completed_taks=fields.Integer('No. of Completed Tasks',compute="_get_completed_tasks",store=True)
    esclation=fields.Integer('Esclations')
    bgv_status=fields.Selection([('Completed','Completed'),('N/A','N/A'),('In Progress','IN Progress')],'BGV Status',default='In Progress',required=True)
    additional_info=fields.Text('Additional Information')
    type=fields.Selection([('Contractor','Contractor'),('Payroll','Payroll'),('Payroll Outsource','Payroll Outsource')],'Payroll')
    employee_source=fields.Selection([('Internal','Internal'),('Outsource','Outsource')],'Source')
    employee_salary=fields.Selection([('Bill to Client','Bill to Client'),('Internal Expense','Internal Expense')],'Salary')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    partner_name=fields.Char("Applicant's Name")
    last_name=fields.Char('Last Name')
    skyp_id=fields.Char('Skype Contact')
    degree_id=fields.Many2one('hr.recruitment.degree','Degree')
    applicant_nature=fields.Selection([('Individual','Individual'),('Company','Company')],'Applicant Nature')
    recruiter_id=fields.Many2one('res.users','Recruiter')
    priority=fields.Selection([('0','Normal'),('1','Good'),('2','Very Good'),('3','Excellent')],'Appreciation')
    medium_id=fields.Many2one('utm.medium','Medium')
    source_id=fields.Many2one('utm.source','Source')
    
    house_no=fields.Char('Flat/House No.')
    street=fields.Char('Street/Society')
    state_id=fields.Many2one('res.country.state')
    city=fields.Char('City')
    zip=fields.Integer('Zip')
    country=fields.Many2one('res.country','Country')
    
    shortlisted_fte=fields.Selection([('Yes','Yes'),('No','No')],'Available for Full Time?')
    dispatch=fields.Selection([('Yes','Yes'),('No','No')],'Available for Dispatch?')
    part_time=fields.Selection([('Yes','Yes'),('No','No')],'Available for Part Time?')
    work_experience=fields.Integer('Relevant Years of Experience')
    partner=fields.Many2one('hr.employee','Partner')
    work_rights_status=fields.Selection([('Yes','Yes'),('No','No')],'Work Rights Verified?')
    primary_category=fields.Selection([('Freelancer','Freelancer'),('Student','Student'),('Part Time Work','Part Time Work'),('Full Time','Full Time'),('Service Provider','Service Provider'),('Local Partner','Local Partner'),('Regional Partner','Regional Partner')],'Resource Primary Category')
    cv_review_score=fields.Float('CV Review Score')
    interview_result_score=fields.Float('Interview Result Score')
    
    salary_expected=fields.Float('Expected Salary')
    salary_expected_extra=fields.Char('Extra Advantages')
    salary_proposed=fields.Float('Proposed Salary')
    salary_proposed_extra=fields.Char('Extra Advantages')
    availability=fields.Date('Availability')
    notice_period=fields.Char('Notice Period')
    applied_job_id=fields.Many2one('hr.job','Applied Job')
    opportunity_id=fields.Many2one('crm.lead','Opportunity')
    customer=fields.Char('Customer')
    cusotmer_project=fields.Char('Project')
    application_summary=fields.Text('Application Summary')
    background_check_report_name=fields.Char('Background Check Report')
    drug_screen_report_name=fields.Char('Drug Screen Report')
class HREmployee(models.Model):
    _inherit='hr.employee'
    
#     partner_id = fields.Many2one('res.partner', string='Related Partner',
#                                  required=True, ondelete='restrict',
#                                  delegate=True, auto_join=True)
    name=fields.Char(compute="_cal_name",store=True)
    state=fields.Selection([('Draft','Draft'),('Current','Current'),('Former','Former')],'State',default='Draft',store=True)
    employee_type=fields.Selection([('Employee','Employee'),('Field Service Engineer(Individual)','Field Service Engineer(Individual)'),('Field Service Engineer(Company)','Field Service Engineer(Company)')],'Employee Type')
    day_rate=fields.Float('Day Rate', digits=(12,1))
    hourly_rate=fields.Float('Hourly Rate', digits=(12,1))
    dispatch_half_day_rate=fields.Float('Half Day Rate', digits=(12,1))
    dispatch_monthly_rate=fields.Float('Monthly Rate', digits=(12,1))
    dispatch_ooh_uplift_from=fields.Float('OOH Uplift From' , digits=(12,1))
    dispatch_ooh_uplift_to=fields.Float('OOH Uplift To', digits=(12,1))
    dispatch_weekend_uplift_from=fields.Float('Weekend/Public Holidays Uplift From', digits=(12,1))
    dispatch_weekend_uplift_to=fields.Float('Weekend/Public Holidays Uplift To', digits=(12,1))
    dispatch_milage=fields.Float('Milage(per km)', digits=(12,1))
    
    fte_day_rate=fields.Float('Day Rate', digits=(12,1))
    fte_hourly_rate=fields.Float('Hourly Rate', digits=(12,1))
    fte_half_day_rate=fields.Float('Half Day Rate', digits=(12,1))
    fte_monthly_rate=fields.Float('Monthly Rate', digits=(12,1))
    fte_ooh_uplift_from=fields.Float('OOH Uplift From', digits=(12,1))
    fte_ooh_uplift_to=fields.Float('OOH Uplift To', digits=(12,1))
    fte_weekend_uplift_from=fields.Float('Weekend/Public Holidays Uplift From', digits=(12,1))
    fte_weekend_uplift_to=fields.Float('Weekend/Public Holidays Uplift To', digits=(12,1))
    fte_milage=fields.Float('Milage(per km)', digits=(12,1))
    
    experience=fields.Float('Experience')
    work_right=fields.Binary('Work Rights Copy')
    work_right_name=fields.Char('Work Rights Name')
    work_right_verified=fields.Boolean('Work Right Verified')
    notice_period=fields.Integer('Notice Period')
    vendor_id=fields.Many2one('res.partner','Vendor/Sub Contractor')
    shortlist_fte=fields.Boolean('Shortlist for FTE')
#     dispatch=fields.
    local_language_level=fields.Selection([('A1','A1'),('A2','A2'),('B1','B1'),('B2','B2'),('C1','C1'),('C2','C2')],'Local Language Level')
    english_language_level=fields.Selection([('A1','A1'),('A2','A2'),('B1','B1'),('B2','B2'),('C1','C1'),('C2','C2')],'English Language Level')
    completed_taks=fields.Integer('No. of Completed Tasks',compute="_get_completed_tasks",store=True)
    esclation=fields.Integer('Esclations')
    bgv_status=fields.Selection([('Completed','Completed'),('N/A','N/A'),('In Progress','IN Progress')],'BGV Status',default='In Progress',required=True)
    background_check_report=fields.Binary('Background Check Report')
    background_check_report_name=fields.Char('Background Check Report')
    drug_screen_report=fields.Binary('Drug Screen Report')
    drug_screen_report_name=fields.Char('Drug Screen Report')
    additional_info=fields.Text('Additional Information')
    education_ids=fields.One2many('hr.applicant.education.details','employee_id','Education')
    experience_ids=fields.One2many('hr.applicant.experience.details','employee_id','Experience')
    certification_ids=fields.One2many('hr.applicant.certification.details','employee_id','Certification')
    language_ids=fields.One2many('hr.applicant.languages','employee_id','Languages')
    requirement_ids=fields.One2many('hr.jobs.requirements.details','employee_id','Requirements')
    internal_evalaution_ids=fields.One2many('hr.jobs.internal.evaluation.details','employee_id','Internal Evalaution')
    document_ids=fields.One2many('hr.jobs.documents.details','employee_id','Documents')
    job_ids=fields.One2many('hr.employee.job.details','employee_id','Jobs')
    territory_ids=fields.Many2many('res.city',string='City/Territory')
    type=fields.Selection([('Contractor','Contractor'),('Payroll','Payroll'),('Payroll Outsource','Payroll Outsource')],'Payroll')
    employee_source=fields.Selection([('Internal','Internal'),('Outsource','Outsource')],'Source')
    employee_salary=fields.Selection([('Bill to Client','Bill to Client'),('Internal Expense','Internal Expense')],'Salary')
    applicant_id=fields.Many2one('hr.applicant','Applicant')
    partner_name=fields.Char("Applicant's Name")
    last_name=fields.Char('Last Name')
    skyp_id=fields.Char('Skype Contact')
    categ_ids=fields.Many2many('hr.applicant.category')
    degree_id=fields.Many2one('hr.recruitment.degree','Degree')
    applicant_nature=fields.Selection([('Individual','Individual'),('Company','Company')],'Applicant Nature')
    recruiter_id=fields.Many2one('res.users','Recruiter')
    priority=fields.Selection([('0','Normal'),('1','Good'),('2','Very Good'),('3','Excellent')],'Appreciation')
    medium_id=fields.Many2one('utm.medium','Medium')
    source_id=fields.Many2one('utm.source','Source')
    
    house_no=fields.Char('Flat/House No.')
    street=fields.Char('Street/Society')
    state_id=fields.Many2one('res.country.state')
    city=fields.Char('City')
    zip=fields.Integer('Zip')
    country=fields.Many2one('res.country','Country')
    
    shortlisted_fte=fields.Selection([('Yes','Yes'),('No','No')],'Available for Full Time?')
    dispatch=fields.Selection([('Yes','Yes'),('No','No')],'Available for Dispatch?')
    part_time=fields.Selection([('Yes','Yes'),('No','No')],'Available for Part Time?')
    work_experience=fields.Integer('Relevant Years of Experience')
    partner=fields.Many2one('hr.employee','Partner')
    work_rights_status=fields.Selection([('Yes','Yes'),('No','No')],'Work Rights Verified?')
    primary_category=fields.Selection([('Freelancer','Freelancer'),('Student','Student'),('Part Time Work','Part Time Work'),('Full Time','Full Time'),('Service Provider','Service Provider'),('Local Partner','Local Partner'),('Regional Partner','Regional Partner')],'Resource Primary Category')
    cv_review_score=fields.Float('CV Review Score')
    interview_result_score=fields.Float('Interview Result Score')
    
    salary_expected=fields.Float('Expected Salary')
    salary_expected_extra=fields.Char('Extra Advantages')
    salary_proposed=fields.Float('Proposed Salary')
    salary_proposed_extra=fields.Char('Extra Advantages')
    availability=fields.Date('Availability')
    notice_period=fields.Char('Notice Period')
    applied_job_id=fields.Many2one('hr.job','Applied Job')
    opportunity_id=fields.Many2one('crm.lead','Opportunity')
    customer=fields.Char('Customer')
    cusotmer_project=fields.Char('Project')
    application_summary=fields.Text('Application Summary')
#     
    @api.depends('partner_name','last_name')
    def _cal_name(self):
        for each in self:
            if each.partner_name and each.last_name:
                each.name=str(each.partner_name) +" "+str(each.last_name)
            else:
                each.name="/"
    def _get_completed_tasks(self):
        for each in self:
            project_tasks=self.env['project.task'].search(['&','|','|',('stage_id.name','=','Completed'),('assigned_worker_id','=',each.id),('backfill_engineer_id','=',each.id),('secondary_backfill_id','=',each.id)])
            if project_tasks:
                each.completed_taks=len(project_tasks)
            else:
                each.completed_taks=0
                
    @api.depends('vendor_id','contract_ids')
    def _cal_employee_type(self):
        for employee in self:
            contracts = employee.sudo().contract_ids.filtered(lambda c: c.state == 'open')
            if contracts:
                employee.employee_type='Employee'
            elif employee.vendor_id:
                employee.employee_type='Field Service Engineer(Company)'
            else:
                employee.employee_type='Field Service Engineer(Individual)'
#     def update_multi_jobs(self,employee):
#         if employee.job_id:
#             job_details=self.env['hr.employee.job.details'].search([('job_id','=',employee.job_id.id),('employee_id','=',employee.id)])
#             if not job_details:
#                 vals={'employee_id':employee.id,
#                       'job_id':employee.job_id.id,
#                       'day_rate':employee.day_rate,
#                       'hourly_rate':employee.hourly_rate}
#                 self.env['hr.employee.job.details'].create(vals)
#             else:
#                 job_details.write({'day_rate':employee.day_rate,
#                         'hourly_rate':employee.hourly_rate})
    @api.model
    def create(self,vals):
#         if vals.get('employee_type',False)=='Field Service Engineer(Individual)':
#             vals.update({'fsm_worker': True})
#         elif vals.get('employee_type',False)=='Field Service Engineer(Company)':
#             vals.update({'fsm_partner': True})
#         else:
#             vals.update({'internal_employee': True})
#         vals.update({'name':vals.get('name')})
        res=super(HREmployee,self).create(vals)
        res.applicant_id.emp_id=res.id
#         if res.job_id:
#             job_details_vals={'employee_id':res.id,
#                        'job_id':res.job_id.id,
#                        'hourly_rate':res.hourly_rate,
#                        'day_rate':res.day_rate}
#             job_details=self.env['hr.employee.job.details'].search([('job_id','=',res.job_id.id),('employee_id','=',res.id)])
#             if not job_details:
#                 self.env['hr.employee.job.details'].create(job_details_vals)
        return res
    
    def write(self,vals):
#         job_details_vals={'employee_id':self.id}
# #         if vals.get('employee_type',False)=='Field Service Engineer(Individual)':
# #             vals.update({'fsm_worker': True})
# #         elif vals.get('employee_type',False)=='Field Service Engineer(Company)':
# #             vals.update({'fsm_partner': True})
# #         else:
# #             vals.update({'internal_employee': True})
#         if vals.get('job_id',False):
#             job_details_vals.update({'job_id':vals.get('job_id',False),
#                           })
#         if vals.get('day_rate',False):
#             job_details_vals.update({'day_rate':vals.get('day_rate',False),
#                               })
#         if vals.get('hourly_rate',False):
#             job_details_vals.update({'hourly_rate':vals.get('hourly_rate',False),
#                        })
#         if vals.get('job_id',False):
#             job_id=vals.get('job_id',False)
#             job_details=self.env['hr.employee.job.details'].search([('job_id','=',job_id),('employee_id','=',self.id)])
#             if not job_details:
#                 self.env['hr.employee.job.details'].create(job_details_vals)
#             else:
#                 job_details.write(job_details_vals)
#         else:
#             job_id=self.job_id.id
#             job_details=self.env['hr.employee.job.details'].search([('job_id','=',job_id),('employee_id','=',self.id)])
#             if not job_details:
#                 self.env['hr.employee.job.details'].create(job_details_vals)
#             else:
#                 job_details.write(job_details_vals)
#             
            
        return super(HREmployee, self).write(vals)
    
    def set_employee_current(self,emp):
        user_pool = self.env['res.users']
        try:
            user_obj=self.env['res.users'].search([('login','=',emp.work_email)])
            if not user_obj:
                if not emp.user_id :
                    if emp.employee_type=='Field Service Engineer(Individual)':
                        fsm_worker=True
                        fsm_partner=False
                        internal_employee=False
                    elif emp.employee_type=='Field Service Engineer(Company)':
                        fsm_worker=False
                        fsm_partner=True
                        internal_employee=False
                    elif emp.employee_type=='Employee':
                        fsm_worker=False
                        fsm_partner=False
                        internal_employee=True
                    emp_name = emp.name
                    login_name = emp.work_email
                    user = user_pool.with_context({'default_fsm_worker':fsm_worker,'default_fsm_partner':fsm_partner,'default_internal_employee':internal_employee,'default_email':emp.work_email,'default_is_employee':True,'default_mobile':emp.mobile_phone}).sudo().create({
                                             'name':emp.name,
                                             'company_id':emp.company_id.id,
                                             'company_ids':[(6,0,[emp.company_id.id])],
                                             'login':login_name,
                                            })
        
                    emp.user_id = user.id
            else:
                emp.user_id=user_obj.id
                
        except Exception as e:
            raise ValidationError(e)
        emp.write({'state':'Current'})
    
    def set_current(self):
        self.set_employee_current(self)
    
    def set_former(self):
        self.write({'state':'Former'})
        self.user_id.active=False
        
    def set_draft(self):
        self.write({'state':'Draft'})

class HrJobsDetails(models.Model):
    _name='hr.employee.job.details'
    
    employee_id=fields.Many2one('hr.employee','Employee')
    job_id=fields.Many2one('hr.job','Job')
    day_rate=fields.Float('Day Rate (USD)')
    hourly_rate=fields.Float('Hourly Rate (USD)')
    total_jobs=fields.Integer('Total Jobs',compute='_cal_total_jobs')
    avg_rating=fields.Float('Avg. Rating',compute='_cal_avg_rating')
    last_assignment=fields.Date('Last Assignment')
    
    @api.depends('job_id','employee_id')
    def _cal_total_jobs(self):
        for each in self:
            if each.employee_id and each.job_id:
                service_order=self.env['project.task'].search(['|','|',('assigned_worker_id','=',each.employee_id.id),('backfill_engineer_id','=',each.employee_id.id),('secondary_backfill_id','=',each.employee_id.id),('job_id','=',each.job_id.id)]).ids
                each.total_jobs=len(service_order)
            else:
                each.total_jobs=0
    
    @api.depends('job_id','employee_id')
    def _cal_avg_rating(self):
        for each in self:
            if each.employee_id and each.job_id:
                total_rating=0
                service_order=self.env['project.task'].search(['|','|',('assigned_worker_id','=',each.employee_id.id),('backfill_engineer_id','=',each.employee_id.id),('secondary_backfill_id','=',each.employee_id.id),('job_id','=',each.job_id.id)])
                for so in service_order:
                    total_rating+=so.rating
                if service_order:
                    each.avg_rating=total_rating/len(service_order)
                else:
                    each.avg_rating=0
            else:
                each.avg_rating=0