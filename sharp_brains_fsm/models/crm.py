from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError

class CRM(models.Model):
    _inherit='crm.lead'
    name = fields.Char(
        'Opportunity', index=True, required=True,
        compute='_compute_name', readonly=True, default='/',store=True)
    number=fields.Char('Number')
   
    partner_id=fields.Many2one(domain="[('customer_rank','!=',0),('type','=','contact')]")
    end_cutomer_id=fields.Many2one('res.partner',domain="[('type','=','end_customer'),('parent_id','=',partner_id)]")
    project_id=fields.Many2one('project.project','Project',domain="['|',('partner_id','=',partner_id),('misc_project','=',True)]")
    job_id=fields.Many2one('hr.job','Skill Type')
    start_date=fields.Date('Start Date')
    coverage=fields.Selection([('In Progress','In Progress'),('Yes','Yes'),('No','No')],'Coverage')
    customer_country=fields.Char('Country',related='partner_id.country_id.name')
    customer_state=fields.Char('State',related='partner_id.state_id.name')
    customer_city=fields.Char('City',related='partner_id.city')
    assign_date=fields.Date('Assign Date')
    team_lead=fields.Many2one('res.users','Team Lead',related='team_id.user_id')
    sd_manager=fields.Many2one('hr.employee','Service Delivery Manager',domain="[('state','=','Current'),('employee_type','=','Employee')]")
    job_application_ids=fields.One2many('hr.applicant','opportunity_id','Applications')
    service_orders_ids=fields.One2many('project.task','opportunity_id','Service Orders')
    service_order_count = fields.Integer('Service Order Count', compute="_compute_service_order_count")
    partner_invoice_id=fields.Many2one('res.partner','Bill To Customer',domain="[('parent_id','=',partner_id),('type','=','invoice')]")
    tikcet_ids=fields.One2many('helpdesk.ticket','opportunity_id','Tickets')
    ticket_count = fields.Integer('Tickets Count', compute="_compute_ticket_count")
    
    def action_new_quotation(self):
        action = super(CRM, self).action_new_quotation()
        product_obj=self.env['product.product'].search([('name','=',self.job_id.name),('type','=','service')],limit=1)
        action['context'] = {
            'default_product_id': product_obj.id,
            'default_partner_invocie_id':self.partner_id.id,
            'default_partner_id':self.end_cutomer_id.id,
            'default_opportunity_id': self.id,
        }
        return action
    
    @api.onchange('project_id')
    def project_onchange(self):
        if self.project_id:
            self.partner_invoice_id=self.project_id.partner_invoice_id.id
    def _compute_ticket_count(self):
        for each in self:
            if type(each.id) is int:
                each.ticket_count=0
                query=self.env.cr.execute("""Select id from helpdesk_ticket where opportunity_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.ticket_count=len(result)
            else:
                each.ticket_count=0
    def action_view_ticket(self):        
        action = self.env.ref('helpdesk.helpdesk_ticket_action_main_tree').sudo().read()[0]
        
        action['context'] = {
#             'default_service_order_source':'Opportunity',
            'default_opportunity_id': self.id,
            'default_partner_id': self.partner_id.id
        }
        query=self.env.cr.execute("""Select id from helpdesk_ticket where opportunity_id="""+str(self.id))
        result=self.env.cr.fetchall()
        ticket_list=[each[0] for each in result]
        action['domain'] = [('id','in',ticket_list)]
        return action
    
    def _compute_service_order_count(self):
        for each in self:
            if type(each.id) is int:
                each.service_order_count=0
                query=self.env.cr.execute("""Select id from project_task where opportunity_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.service_order_count=len(result)
            else:
                each.service_order_count=0
    def action_view_service_order(self):        
        action = self.env.ref('project.action_view_all_task').sudo().read()[0]
        action['context'] = {
            'default_service_order_source':'Opportunity',
            'default_opportunity_id': self.id,
        }
        query=self.env.cr.execute("""Select id from project_task where opportunity_id="""+str(self.id))
        result=self.env.cr.fetchall()
        task_list=[each[0] for each in result]
        action['domain'] = [('id','in',task_list)]
        return action
    
    @api.model
    def create(self, vals):
        res = super(CRM, self).create(vals)
        res.number='OPP'+str(res.id).zfill(8)
        return res
    def _cal_number(self):
        for each in self:
            code = self.env['ir.sequence'].next_by_code('todo.task')
            self.number=code
    @api.depends('partner_id','project_id','job_id')
    def _compute_name(self):
        for lead in self:
            if lead.name and lead.partner_id and lead.partner_id.name and lead.project_id and lead.job_id:
                lead.name = str(lead.partner_id.name)+" - "+str(lead.project_id.name)+" - "+str(lead.job_id.name)
    
    def action_view_sale_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        product_obj=self.env['product.product'].search([('name','=',self.job_id.name),('type','=','service')],limit=1)
        action['context'] = {
            'search_default_draft': 1,
            'search_default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id,
            'default_project_id': self.project_id.id,
            'default_product_id':product_obj.id,
            'default_partner_invocie_id':self.partner_id.id,
            'default_partner_id':self.end_cutomer_id.id
        }
        action['domain'] = [('opportunity_id', '=', self.id), ('state', 'in', ['draft', 'sent'])]
        quotations = self.mapped('order_ids').filtered(lambda l: l.state in ('draft', 'sent'))
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

