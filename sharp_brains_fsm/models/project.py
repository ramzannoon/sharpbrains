from openerp import _, models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import UserError,ValidationError
from pyexpat import model
import pytz
from datetime import datetime, timedelta
from _datetime import date
from odoo.addons.base.models.res_partner import _tz_get

class TimerTimer(models.Model):
    _inherit = 'timer.timer'
    start_date=fields.Datetime('Start Date')
    end_date=fields.Datetime('End Date')
    def action_timer_start(self):
        check_in=fields.Datetime.now()
        if self.res_model=='project.task':
            task_obj=self.env['project.task'].search([('id','=',self.res_id)])
            if task_obj:
                old_tz = pytz.timezone('UTC')
                new_tz = pytz.timezone(task_obj.tz)
                dt = datetime.now(new_tz)
                str_time = dt.strftime("%H:%M")
                check_in_date = datetime.strptime(str_time, "%H:%M").time()
#                 if task_obj.fte_attendance:
#                     week_day=dt.weekday()
                query = """SELECT id FROM planning_slot where task_id="""+str(task_obj.id)+""" and DATE(start_datetime)='"""+str(fields.Datetime.now().date())+"""'"""
                self.env.cr.execute(query)
                schedule_id = self.env.cr.fetchone()
                schedule_line=self.env['planning.slot'].search([('id','in',schedule_id)])
                if schedule_line:
#                         result='{0:02.0f}:{1:02.0f}'.format(*divmod(schedule_line.hour_from * 60, 60))
                    start_date = schedule_line.start_datetime
#                     start_date=start_date(new_tz)
                    start_time=start_date.time()
                    start_hour=start_time.hour
                    
                    seconds = start_hour *60*60
                else: 
                    raise ValidationError('Schedule planning entery not exist for today in worksite schedule, please contact system administrator.')
#                 else:
#                     start_date = task_obj.start_at.time()
#                     seconds = task_obj.start_at.timestamp()
#                 t1 = timedelta(hours=check_in_date.hour, minutes=check_in_date.minute)
#                 t2 = timedelta(hours=start_date.hour, minutes=start_date.minute)
                
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)
                if check_in_date<start_time:
                   check_in=fields.Datetime.now().replace(hour=int(hours), minute=int(minutes),second=0,microsecond=0)
                task_obj.write({'display_timer_stop':True})
        if not self.timer_start:
            self.write({'timer_start': check_in,
                        'start_date':fields.Datetime.now(),
                        })
    def _get_minutes_spent(self):
        start_time = self.timer_start
        stop_time = fields.Datetime.now()
        if self.res_model=='project.task':
            task_obj=self.env['project.task'].search([('id','=',self.res_id)])
            if task_obj:
                old_tz = pytz.timezone('UTC')
                new_tz = pytz.timezone(task_obj.tz)
                dt = datetime.now(new_tz)
                str_time = dt.strftime("%H:%M")
                check_out_date = datetime.strptime(str_time, "%H:%M").time()
#                 if task_obj.fte_attendance:
                query = """SELECT id FROM planning_slot where task_id="""+str(task_obj.id)+""" and DATE(start_datetime)='"""+str(fields.Datetime.now().date())+"""'"""
                self.env.cr.execute(query)
                schedule_id = self.env.cr.fetchone()
                schedule_line=self.env['planning.slot'].search([('id','in',schedule_id)])
                if schedule_line:
                    end_date = schedule_line.end_datetime
                    end_time=end_date.time()
                    end_hour=end_time.hour
                    seconds = end_hour *60*60
                else: 
                    raise ValidationError('Schedule entery not exist for today in worksite schedule, please contact system administrator.')
#                 else:
#                     stop_date = task_obj.end_at.time()
#                     seconds = task_obj.end_at.timestamp()
#                 t1 = timedelta(hours=check_out_date.hour, minutes=check_out_date.minute)
#                 t2 = timedelta(hours=stop_date.hour, minutes=stop_date.minute)
                
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)
                if check_out_date>end_time:
                   stop_time=stop_time.replace(hour=int(hours), minute=int(minutes),second=0,microsecond=0)
                task_obj.write({'display_timer_stop':False})
        # timer was either running or paused
        if self.timer_pause:
            start_time += (stop_time - self.timer_pause)
        return (stop_time - start_time).total_seconds() / 60,self.start_date,fields.Datetime.now()
class ProjectTaskCreateTimesheet(models.TransientModel):
    _inherit = 'project.task.create.timesheet'
    start_date=fields.Datetime('Start Date')
    end_date=fields.Datetime('End Date')

    def save_timesheet(self):
        values = {
            'task_id': self.task_id.id,
            'project_id': self.task_id.project_id.id,
            'date': fields.Date.context_today(self),
            'name': self.description,
            'user_id': self.env.uid,
            'unit_amount': self.time_spent,
            'start_date':self.start_date,
            'end_date':self.end_date,
        }
        self.task_id.user_timer_id.unlink()
        return self.env['account.analytic.line'].create(values)
    
class AssignServiceOrderWizard(models.TransientModel):
    _name='assign.service.order.wizard'
    def _get_default_available_worker(self):
        if 'active_id' in self.env.context:
            id=self.env.context['active_id']
            available_worker=self.env['hr.available.workers'].sudo().search([('id','=',id)])
            if available_worker:
                return available_worker.id       
            else:
                return None
    worker_id=fields.Many2one('hr.available.workers','Available Worker',default=_get_default_available_worker)
    task_id=fields.Many2one('project.task','Task',required=True)
    employee_id=fields.Many2one('hr.employee','Employee',required=True)
    type=fields.Selection([('Primary Engineer','Primary Engineer'),('Back fill Engineer','Back fill Engineer'),('Secondary Back fill Engineer','Secondary Back fill Engineer')],'Role Type',required=True)
    
    def set_assignee(self):
        if self.type=='Primary Engineer':
            self.task_id.assigned_worker_id=self.employee_id.id
        elif self.type=='Back fill Engineer':
            self.task_id.backfill_engineer_id=self.employee_id.id
        elif self.type=='Secondary Back fill Engineer':
            self.task_id.secondary_backfill_id=self.employee_id.id
        available_worker=self.env['hr.available.workers'].search([('task_id','=',self.task_id.id)])
        for each in available_worker:
            each.task_assigned=False
        self.worker_id.task_assigned=True
        
class HrAvailableWorkers(models.Model):
    _name='hr.available.workers'
    
    task_id=fields.Many2one('project.task','Task')
    employee_id=fields.Many2one('hr.employee')
    employee_type=fields.Selection([('Employee','Employee'),('Field Service Engineer(Individual)','Field Service Engineer(Individual)'),('Field Service Engineer(Company)','Field Service Engineer(Company)')],'Employee Type',default='Employee')
    day_rate=fields.Float('Day Rate (USD)')
    hourly_rate=fields.Float('Hourly Rate (USD)')
    job_id=fields.Many2one('hr.job','Job Position')
    mobile_phone=fields.Char('Work Mobile')
    work_email=fields.Char('Work Email')
    total_jobs=fields.Integer('Total Jobs')
    avg_rating=fields.Float('Avg. Rating')
    last_assignment=fields.Date('Last Assignment')
    task_assigned=fields.Boolean('Task Assigned')
    
class WorkSchedule(models.Model):
    _name='sb.work.schedule.details'
    _order = 'dayofweek, hour_from'
    _rec_name='dayofweek'
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    hour_from = fields.Float(string='Work from', required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', required=True)
    task_id=fields.Many2one('project.task','Task')
    
    _sql_constraints = [
        ('name_uniq', 'unique (dayofweek,task_id)', "Work schedule should be unique for a day!"),
    ]
    
    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 23.99)
        self.hour_to = max(self.hour_to, 0.0)

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)


# class ProjectTaskState(models.Model):
#     _name='project.task.state'
#     name=fields.Char('Name')
    
class ProjectTaskType(models.Model):
    _inherit='project.task.type'
    type=fields.Selection([('Internal Task','Internal Task'),('Service Order','Service Order'),('Both','Both')],'Implement For',default='Internal Task')
    
class ProjectTask(models.Model):
    _inherit='project.task'
    _inherits = {'res.partner': 'partner_id'}
#     external_task_state=fields.Selection([('New','New'),('Requested','Requested'),('Assigned','Assigned'),('Confirmed','Confirmed'),('In Progress','In Progress'),('Completed','Completed'),('Cancelled','Cancelled')],'State',default='New')

    ticket_id=fields.Many2one('helpdesk.ticket','Helpdesk Ticket')
    task_type=fields.Selection([('Internal Task','Internal Task'),('Service Order','Service Order')],'Type',default='Service Order')
    number=fields.Char('Number',default='/')
    priority=fields.Selection([('0','All'),('1','Low Priority'),('2','High Priority'),('Urgent','Urgent')],'Priority')
    sla=fields.Many2one('sb.sla','SLA')
    customer_id=fields.Many2one('res.partner','Customer')
    site_id=fields.Many2one('res.partner','Work Site',domain="[('parent_id','=',partner_id),('type','=','work_site')]")
    dispatcher_id=fields.Many2one('res.users','Dispatcher',default=lambda self: self.env.user)
    agreement_id=fields.Many2one('agreement','Agreement')
    client_id=fields.Many2one('res.partner','Client')
    country_id=fields.Many2one('res.country','Country',related='site_id.country_id',store=True)
    state_id=fields.Many2one('res.country.state','State',related='site_id.state_id',store=True)
    city=fields.Char('City/Territory',related='site_id.city',store=True)
    email=fields.Char('Email',related='site_id.email',store=True)
    sit_partner_id=fields.Many2one('res.partner')
#     mobile=state_id=fields.Char('Mobile',related='site_id.mobile')
    phone=fields.Char('Phone',related='site_id.phone')
    team_id=fields.Many2one('project.team','Team')
    assigned_worker_id=fields.Many2one('hr.employee','Primary Engineer')
    backfill_engineer_id=fields.Many2one('hr.employee','Back fill Engineer')
    secondary_backfill_id=fields.Many2one('hr.employee','Secondary Back fill Engineer')
    service_order_source=fields.Selection([('Opportunity','Opportunity'),('Ticket','Ticket')],'Source')
    opportunity_id=fields.Many2one('crm.lead','Opportunity')
    action_plan=fields.Html('Action Plan(SOW)')
#     
    job_id=fields.Many2one('hr.job','Work Type/Job')
    job_ids=fields.Many2many('hr.job','task_jobs_rel','job_id','task_id','Jobs',compute='_get_valid_jobs')
    hourly_rate=fields.Float('Hourly Rate')
    day_rate=fields.Float('Day Rate')
    monthly_rate=fields.Float('Monthly Rate')
    schedule_id=fields.Many2one('resource.calendar','Work Schedule')
    
    tz_offset = fields.Char(
        string="Work-Site Timezone", readonly=True, compute="_compute_tz_name"
    )
    
    tz = fields.Char(related="site_id.tz", string="Timezone")
    tz_datetime = fields.Char(
        string="Starting At (Work-Site Local Time)",
        readonly=True,
        save=True,
    )
#     
    start_date=fields.Date('Starting At (Work-Site)')
#     
    allday=fields.Boolean('Allday')
# #     
    end_date=fields.Date('Ending At (Work-Site)')
    duration=fields.Float('Duration')
    start_at=fields.Datetime('Starting At (Work-Site)',default=fields.Date.today,
        compute='_compute_stop', readonly=False, store=True,)
    end_at=fields.Datetime('Ending At (Work-Site)',default=fields.Date.today,
        compute='_compute_stop', readonly=False, store=True,)
    work_start=fields.Float('Shift Start Time')
    work_end =fields.Float('Shift End Time')
    
    requirement_ids=fields.One2many('hr.jobs.requirements.details','task_id','Requirements')
    required_material=fields.Html('Required Material')
    work_instruction=fields.Html('Work Instruction')
    site_instruction=fields.Html('Site Instruction')
    resolution_notes=fields.Html('Resolution Notes')
    rating=fields.Selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')],'Rating (At the time of closing)')
    available_workers=fields.One2many('hr.available.workers','task_id','Available Workers',compute="_get_available_workers",store=True)
#     timesheet_ids=fields.One2many('account.analytic.line','task_id','Timesheet')
#     tz = fields.Char(string='Timezone', related="site_id.tz")
    commercial_partner_id = fields.Many2one('res.partner')
    work_schedule_ids=fields.One2many('sb.work.schedule.details','task_id','Work Schedule')
    fte_attendance=fields.Boolean('FTE Attendance',default=False,compute='_cal_type',store=True)
    planning_ids=fields.One2many('planning.slot','task_id','Scheduule Planning')
    planning_count = fields.Integer('Schedule Count', compute="_compute_schedule_count")
    
    def _compute_schedule_count(self):
        for each in self:
            if type(each.id) is int:
                each.planning_count=0
                query=self.env.cr.execute("""Select id from planning_slot where task_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.planning_count=len(result)
            else:
                each.planning_count=0
                
    def action_view_schedule_planning(self):        
        action = self.env.ref('planning.planning_action_schedule_by_employee').sudo().read()[0]
        action['context'] = {
#             'default_service_order_source':'Opportunity',
            'default_task_id': self.id,
            'default_employee_id': self.assigned_worker_id.id
        }
        query=self.env.cr.execute("""Select id from planning_slot where task_id="""+str(self.id))
        result=self.env.cr.fetchall()
        schedule_list=[each[0] for each in result]
        action['domain'] = [('id','in',schedule_list)]
        return action
    
    @api.onchange('fte_attendance')
    def on_change_fte_attendance(self):
        for record in self:
            if record.fte_attendance:
            # record.jv_break_time = False
                record.write({'work_schedule_ids':
                    [
                        (0, 0, {'dayofweek': '0', 'hour_from': 9.0,
                                'hour_to': 17.0, }),
                        (0, 0, {'dayofweek': '1', 'hour_from': 9.0,
                                'hour_to': 17.0, }),
                        (0, 0, {'dayofweek': '2', 'hour_from': 9.0,
                                'hour_to': 17.0, }),
                        (0, 0, {'dayofweek': '3', 'hour_from': 9.0,
                                'hour_to': 17.0, }),
                        (0, 0, {'dayofweek': '4', 'hour_from': 9.0,
                                'hour_to': 17.0, }),
                    ]
                })
    
    @api.depends('sla')
    def _cal_type(self):
        for each in self:
            if each.sla.name=='Monthly Rate':
                each.fte_attendance=True
            else:
                each.fte_attendance=False
    
    
    @api.depends("site_id")
    def _compute_tz_name(self):
        for rec in self:
            if rec.site_id:
                rec_tz = rec.site_id.tz
                tz_offset = datetime.now(pytz.timezone(rec_tz)).strftime("%z")
                rec.tz_offset = "%s (%s)" % ((rec_tz), (tz_offset))
            else:
                rec.tz_offset=""
    
#     @api.depends('start_date','start_at','site_id','tz')
#     def _compute_datetime_timezone(self):
#         for rec in self:
#             if rec.start_date:
#                 if rec.tz:
#                     site_local_timezone = pytz.timezone(self.tz)
#                     site_local_dt = pytz.utc.localize(
#                         rec.start_date
#                     ).astimezone(site_local_timezone)
#  
#                     rec.tz_datetime = site_local_dt
#                 else:
#                     raise UserError(_("Please select Work Site First."))
#             elif rec.start_at:
#                 if rec.tz:
#                     site_local_timezone = pytz.timezone(self.tz)
#                     site_local_dt = pytz.utc.localize(
#                         rec.start_at
#                     ).astimezone(site_local_timezone)
#  
#                     rec.tz_datetime = site_local_dt
#                 else:
#                     raise UserError(_("Please select Work Site First."))
#             else:
#                 rec.tz_datetime=None
                
    def _get_last_sol_of_customer(self):
        # Get the last SOL made for the customer in the current task where we need to compute
        self.ensure_one()
        if not self.commercial_partner_id or not self.allow_billable:
            return False
        domain = [('company_id', '=', self.company_id.id), ('is_service', '=', True), ('work_site_id', '=', self.site_id.id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done'])]
        if self.project_id.bill_type == 'customer_project' and self.project_sale_order_id:
            domain.append(('order_id', '=?', self.project_sale_order_id.id))
        sale_lines = self.env['sale.order.line'].search(domain)
        for line in sale_lines:
            if line.remaining_hours_available and line.remaining_hours > 0:
                return line
        return False
#     @api.onchange('project_id')
#     def _onchange_project(self):
#         if self.project_id and self.project_id.bill_type == 'customer_project':
#             if not self.partner_id:
#                 self.partner_id = self.project_id.partner_id
#             if not self.sale_line_id:
#                 self.sale_line_id = self.project_id.sale_line_id
    @api.onchange('name','sequence','number','date_deadline','tag_ids','sla','dispatcher_id','client_id','task_type','project_id','user_id','priority','partner_id','site_id','city','team_id')
    def cal_assignment(self):
        if self.site_id:
            if not self.assigned_worker_id:
                self.assigned_worker_id=self.site_id.assigned_worker_id.id 
            if not self.backfill_engineer_id:
                self.backfill_engineer_id=self.site_id.backfill_engineer_id.id
            if not self.secondary_backfill_id:
                self.secondary_backfill_id=self.site_id.secondary_backfill_id.id
    def action_timer_stop(self):
        # timer was either running or paused
        if self.user_timer_id.timer_start and self.display_timesheet_timer:
            minutes_spent,start_date,end_date = self.user_timer_id._get_minutes_spent()
#             minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_min_duration', 0))
#             rounding = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_rounding', 0))
#             minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
            return self._action_open_new_timesheet(minutes_spent * 60 / 3600,start_date,end_date)
        return False
    
    def _action_open_new_timesheet(self, time_spent,start_date,end_date):
        return {
            "name": _("Confirm Time Spent"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.task.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': self._name,
                'default_time_spent': time_spent,
                'default_start_date': start_date,
                'default_end_date': end_date,
            },
        }
        
    @api.depends('project_id')
    def _get_valid_jobs(self):
        for each in self:
            if each.project_id:
                job_list=[]
                if each.project_id.sale_order_id:
                    for line in each.project_id.sale_order_id.order_line:
                        job_obj=self.env['hr.job'].search([('name','=',line.product_id.name)])
                        if job_obj:
                            job_list.append(job_obj.id)
                    each.job_ids=job_list
                else:
                    job_obj=self.env['hr.job'].search([])
                    each.job_ids=job_obj.ids
            else:
                each.job_ids=None
    @api.depends('job_id','site_id')
    def _get_available_workers(self):
        for each in self:
            if each.available_workers:
                each.available_workers.unlink()
            if each.job_id and each.site_id:
                employee_list=[(5,0,0)]
                for k in each.site_id.city_id.employee_ids:
                    job_details=self.env['hr.employee.job.details'].search([('job_id','=',each.job_id.id),('employee_id.state','=','Current'),('employee_id','=',k.id)])
                    for j in job_details:
                        records={
                            'employee_id':j.employee_id.id or False,
                            'job_id':j.job_id.id or False,
                            'day_rate':j.day_rate or False,
                            'hourly_rate':j.hourly_rate or False,
                            'total_jobs':j.total_jobs or False,
                            'avg_rating':j.avg_rating,
                            'last_assignment':j.last_assignment,
                            'task_id':each.id
                            }
                        employee_list.append((0,0,records))
                each.available_workers=employee_list
            else:
                each.available_workers=None          
    @api.onchange('job_id')
    def onchange_job(self):
        if self.job_id:
            self.requirement_ids.unlink()
#             self.requirement_ids=self.job_id.requirements_ids
            job_list=[(5,0,0)]
            for each in self.job_id.requirements_ids:
                records={
                    'sequence':each.sequence or False,
                    'skill_type':each.type or False,
                    'skill_id':each.id or False
                    }
                job_list.append((0,0,records))
            self.requirement_ids=job_list
#     def set_requested(self):
#         self.write({'external_task_state':'Requested'})
#     
#     def set_assigned(self):
#         self.write({'external_task_state':'Assigned'})
#     
#     def set_confirmed(self):
#         self.write({'external_task_state':'Confirmed'})
#     
#     def set_completed(self):
#         self.write({'external_task_state':'Completed'})
#         stage_obj=self.env['project.task.type'].search([('name','=','Completed')])
#         if stage_obj:
#             self.write({'stage_id':stage_obj.id})
#     
#     def set_inprogress(self):
#         self.write({'external_task_state':'In Progress'})
#         stage_obj=self.env['project.task.type'].search([('name','=','In Progress')])
#         if stage_obj:
#             self.write({'stage_id':stage_obj.id})
#     def set_done(self):
#         self.write({'external_task_state':'Done'})
#     
#     def set_cancelled(self):
#         self.write({'external_task_state':'Cancelled'})
#         stage_obj=self.env['project.task.type'].search([('name','=','Cancelled')])
#         if stage_obj:
#             self.write({'stage_id':stage_obj.id})
        
        
    @api.model
    def create(self,vals):
        res=super(ProjectTask,self).create(vals)
        res.number=str(res.id).zfill(6)
        if res.fte_attendance:
            res.write({'work_schedule_ids':
                        [
                            (0, 0, {'dayofweek': '0', 'hour_from': 9.0,
                                    'hour_to': 17.0, }),
                            (0, 0, {'dayofweek': '1', 'hour_from': 9.0,
                                    'hour_to': 17.0, }),
                            (0, 0, {'dayofweek': '2', 'hour_from': 9.0,
                                    'hour_to': 17.0, }),
                            (0, 0, {'dayofweek': '3', 'hour_from': 9.0,
                                    'hour_to': 17.0, }),
                            (0, 0, {'dayofweek': '4', 'hour_from': 9.0,
                                    'hour_to': 17.0, }),
                        ]
                    })
        return res
    
    
    @api.depends('allday', 'start_at', 'end_at')
    def _compute_dates(self):

        for service_order in self:
            if service_order.allday and service_order.start_at and service_order.end_at:
                service_order.start_date = service_order.start_at.date()
                service_order.end_date = service_order.end_at.date()
            else:
                service_order.start_date = False
                service_order.end_date = False
    
    @api.depends('start_at', 'duration')
    def _compute_stop(self):
        # stop and duration fields both depends on the start field.
        # But they also depends on each other.
        # When start is updated, we want to update the stop datetime based on
        # the *current* duration. In other words, we want: change start => keep the duration fixed and
        # recompute stop accordingly.
        # However, while computing stop, duration is marked to be recomputed. Calling `event.duration` would trigger
        # its recomputation. To avoid this we manually mark the field as computed.
        duration_field = self._fields['duration']
        self.env.remove_to_compute(duration_field, self)
        for service_order in self:
            # Round the duration (in hours) to the minute to avoid weird situations where the event
            # stops at 4:19:59, later displayed as 4:19.
            service_order.end_at = service_order.start_at + timedelta(minutes=round((service_order.duration or 1.0) * 60))
            if service_order.allday:
                service_order.end_at -= timedelta(seconds=1)
    
    @api.depends('end_at', 'start_at')
    def _compute_duration(self):
        for service_order in self:
            service_order.duration = self._get_duration(service_order.start_at, service_order.end_at)
    
    def _get_duration(self, start, stop):
        """ Get the duration value between the 2 given dates. """
        if not start or not stop:
            return 0
        duration = (stop - start).total_seconds() / 3600
        return round(duration, 2)
class Project(models.Model):
    _inherit='project.project'
    project_type=fields.Selection([('Internal Project','Internal Project'),('Customer Project','Customer Project')],'Type')
    opportunity_id=fields.Many2one('crm.lead','Opportunity',domain="[('type','!=','lead')]")
    misc_project=fields.Boolean('Misc. Project')
    state=fields.Selection([('In Progress','In Progress'),('Completed','Completed'),('Canceleld','Canceleld')],'State',default='In Progress')
    worksite_ids=fields.One2many('res.partner','x_project_id','Worksites')
    worksite_count = fields.Integer('Worksites Count', compute="_compute_worksites_count")
    partner_id=fields.Many2one(domain="[('type','=','contact'),('customer_rank','=',1)]",string='Client (Billing Customer)')
    partner_invoice_id=fields.Many2one('res.partner','End Customer',domain="[('parent_id','=',partner_id),('type','=','end_customer')]")
    pc= fields.Char('PC')
    sdm= fields.Char('SDM')
    client_sdm= fields.Char('Client SDM')
    
    def _compute_worksites_count(self):
        for each in self:
            if type(each.id) is int:
                each.worksite_count=0
                query=self.env.cr.execute("""Select id from res_partner where type='work_site' and x_project_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.worksite_count=len(result)
            else:
                each.service_order_count=0
    def action_view_worksite(self):        
        action = self.env.ref('sharp_brains.action_partner_worksites').sudo().read()[0]
        action['context'] = {
            'default_x_project_id':self.id,
            'default_parent_id':self.partner_id.id,
            'default_type':'work_site',
            'default_customer_rank':1,
            'default_active':True,
            'default_is_company':False,
            'default_partner_share':True,
            'default_invoice_warn':False,
            'default_purchase_warn':False,
            'default_sale_warn':False,
            'default_is_published':False
        }
        query=self.env.cr.execute("""Select id from res_partner where type='work_site' and x_project_id="""+str(self.id))
        result=self.env.cr.fetchall()
        worksite_list=[each[0] for each in result]
        action['domain'] = [('id','in',worksite_list)]
        return action
#     assigned_worker_id=fields.Many2one('hr.employee','Primary Engineer')
#     backfill_engineer_id=fields.Many2one('hr.employee','Back fill Engineer')
#     secondary_backfill_id=fields.Many2one('hr.employee','Secondary Back fill Engineer')
#     type=fields.Selection([('Project Based','Project Based'),('On Demand','On Demand')],default='Project Based')
    @api.model
    def create(self,vals):
        if not vals.get('project_type',False):
            vals.update({'project_type':'Customer Project'})
        result = super(Project,self).create(vals)
        stages_obj=[]
        if result.project_type=='Internal Project':
            stages_obj = self.env['project.task.type'].search([('type','in',['Internal Task','Both'])])
        elif result.project_type=='Customer Project':
            stages_obj = self.env['project.task.type'].search([('type','in',['Service Order','Both'])])
        for each in stages_obj:
            each.write({'project_ids':[(4, result.id)]})
        return result
#     @api.model
#     def _read_group_stage_ids(self, stages, domain, order):
#         # Call Super Function
#         response = super(Task, self)._read_group_stage_ids(stages, domain, order)
#         search_domain = [('id', 'in', response.ids)]
#         # Append my specifik stages [Stages whose code is equal to todo or inprogress or done or canceled]
# #         if self.
#         search_domain = ['|', ('code', 'in', ['todo', 'inprogress', 'done', 'canceled'])] + search_domain
#         stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
#         return stages.browse(stage_ids)
# 
# 
# class WorkSite(models.Model):
#     _name='sb.work.site'
#     name=fields.Char('Name',requred=True)
#     site_owner_id=fields.Many2one('res.partner','Site Owner')
#     end_customer=fields.Many2one('res.partner','End Customer')
#     
class Agreement(models.Model):
    _name='agreement'
    name=fields.Char('Name',requred=True)
# 
class ProjectTeam(models.Model):
    _name='project.team'
    _description = 'Field Service Team'

    name = fields.Char(required=True, translation=True)
    description = fields.Text(translation=True)
    sequence = fields.Integer('Sequence', default=1,
                              help="Used to sort teams. Lower is better.")
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.user.company_id,
        help="Company related to this team")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Team name already exists!"),
    ]
# 
class AccountAnalyticLine(models.Model):
    _inherit='account.analytic.line'
    start_date=fields.Datetime('Actual Start Date')
    end_date=fields.Datetime('Actual End Date')
    actual_duration=fields.Float('Actual Duration',compute='cal_actual_duration')
    
    @api.depends('start_date','end_date')
    def cal_actual_duration(self):
        for each in self:
            if each.start_date and each.end_date:
                duration=(each.end_date - each.start_date).total_seconds() / 60
                each.actual_duration=duration * 60 / 3600
            else:
                each.actual_duration=0
    
class FTEAttendance(models.TransientModel):
    _name='sb.fte.attendance'
    _rec_name='employee_id'
    def _get_employee(self):
        employee_obj=self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        if employee_obj:
            return employee_obj.id 
        else:
            return None
    
    def _get_default_project(self):
        employee_obj=self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        task_obj=self.env['project.task'].search(['|','|',('assigned_worker_id','=',employee_obj.id),('backfill_engineer_id','=',employee_obj.id),('secondary_backfill_id','=',employee_obj.id),('stage_id.name','in',['Assigned','Confirmed','In Progress','Completed']),('fte_attendance','=',True)],order='id asc')
        if len(task_obj)==1:
            return task_obj.project_id.id 
        elif len(task_obj)>1:
            return task_obj[0].project_id.id
        else:
            return None
    
    def _get_default_task(self):
        employee_obj=self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        task_obj=self.env['project.task'].search(['|','|',('assigned_worker_id','=',employee_obj.id),('backfill_engineer_id','=',employee_obj.id),('secondary_backfill_id','=',employee_obj.id),('stage_id.name','in',['Assigned','Confirmed','In Progress','Completed']),('fte_attendance','=',True)],order='id asc')
        if len(task_obj)==1:
            return task_obj.id 
        elif len(task_obj)>1:
            return task_obj[0].id
        else:
            return None
    employee_id=fields.Many2one('hr.employee', default=_get_employee)
    project_id=fields.Many2one('project.project',default=_get_default_project)
    task_id=fields.Many2one('project.task','Service Order',domain="['|','|',('assigned_worker_id','=',employee_id),('backfill_engineer_id','=',employee_id),('secondary_backfill_id','=',employee_id),('stage_id.name','in',['Assigned','Confirmed','In Progress','Completed']),('project_id','=',project_id),('fte_attendance','=',True)]",default=_get_default_task)
    display_timer_start_primary=fields.Boolean(related='task_id.display_timer_start_primary')
    display_timer_start_secondary=fields.Boolean(related='task_id.display_timer_start_secondary')
    display_timer_stop=fields.Boolean(related='task_id.display_timer_stop')
    
    display_timer_start=fields.Boolean('Display Timer Start')
    
    @api.onchange('employee_id')
    def get_project(self):
        res = {}
        project_list=[]
        if self.employee_id:
            task_obj=self.env['project.task'].search(['|','|',('assigned_worker_id','=',self.employee_id.id),('backfill_engineer_id','=',self.employee_id.id),('secondary_backfill_id','=',self.employee_id.id),('stage_id.name','in',['Assigned','Confirmed','In Progress','Completed'])])
            for each in task_obj:
                project_list.append(each.project_id.id)
            if project_list:
                res['domain']={'project_id':[('id','in',project_list)]}
                return res
            else:
                res['domain']={'project_id':[('id','=',-1)]}
                return res
    def start_timer(self):
        return self.task_id.action_timer_start()
    
    def start_stop(self):
        return self.task_id.action_timer_stop()
#         self.task_id.display_timer_stop=False
#         self.task_id.display_timer_start_primary=True
    