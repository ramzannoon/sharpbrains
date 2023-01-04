from openerp import models, fields, api, exceptions
from odoo import api, fields, models, _
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError


class HelpdeskTicket(models.Model):
    _inherit='helpdesk.ticket'
    project_id=fields.Many2one('project.project','Project',domain="[('partner_id','=',partner_id)]")
    work_site_id=fields.Many2one('res.partner',domain="[('parent_id','=',partner_id),('type','=','work_site')]")
    sale_order_id = fields.Many2one('sale.order', string='Ref. Sales Order',
        domain="""[('company_id', '=', company_id),('partner_id','=',partner_id)]""",
        help="Reference of the Sales Order to which this ticket refers. Setting this information aims at easing your After Sales process and only serves indicative purposes.")
    so_line_id = fields.Many2one('sale.order.line', string='SO Line',domain="[('order_id','=',sale_order_id),('work_site_id','=',work_site_id)]")
    country_id=fields.Many2one('res.country','Country',related='work_site_id.country_id')
    state_id=fields.Many2one('res.country.state','State',related='work_site_id.state_id')
    city=fields.Char('City/Territory',related='work_site_id.city')
    phone=fields.Char('Phone',related='work_site_id.phone')
    mobile=fields.Char('Mobile',related='work_site_id.mobile')
    category_id=fields.Many2one('helpdesk.ticket','Category')
    channel=fields.Char('Channel')
    other_info=fields.Text('Other Information')
    service_orders_ids=fields.One2many('project.task','ticket_id','Service Orders')
    service_order_count = fields.Integer('Service Order Count', compute="_compute_service_order_count")
    opportunity_id=fields.Many2one('crm.lead','Opportunity')
    
    def create_service_order(self):
        service_order_source='Ticket'
        opportunity_id=None
        ticket_id=self.id
        job_id=self.env['hr.job'].search([('name','=',self.so_line_id.product_id.name)])
        values={'task_type':'Service Order',
                'job_id':job_id.id or False,
                'hourly_rate':self.so_line_id.price_unit,
                'day_rate':self.so_line_id.price_unit*8,
                'project_id':self.sale_order_id.project_id.id,
                'partner_id':self.partner_id.id,
                'site_id':self.work_site_id.id,
                'city':self.work_site_id.city,
                'service_order_source':'Ticket',
                'opportunity_id':None,
                'ticket_id':self.id,
                'name':"/",
                'assigned_worker_id':self.project_id.assigned_worker_id.id,
                'backfill_engineer_id':self.project_id.backfill_engineer_id.id,
                'secondary_backfill_id':self.project_id.secondary_backfill_id.id,
                'sale_order_id':self.sale_order_id.id
                
                }
        task = self.env['project.task'].sudo().create(values)
        task.write({'name':str(task.number)+":"+str(self.sale_order_id.project_id.name)})
#         self.write({'task_id': task.id})
        # post message on task
        task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.sale_order_id.id, self.sale_order_id.name, self.so_line_id.product_id.name)
        task.message_post(body=task_msg)
        return task
    
    def _compute_service_order_count(self):
        for each in self:
            if type(each.id) is int:
                each.service_order_count=0
                query=self.env.cr.execute("""Select id from project_task where ticket_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.service_order_count=len(result)
            else:
                each.service_order_count=0
    def action_view_service_order(self):        
        action = self.env.ref('project.action_view_all_task').sudo().read()[0]
        job_id=self.env['hr.job'].search([('name','=',self.so_line_id.product_id.name)])
        action['context'] = {
            'default_project_id':self.project_id.id,
            'default_site_id':self.work_site_id.id,
            'default_sale_order_id':self.sale_order_id.id,
            'default_sale_line_id':self.so_line_id.id,
            'default_service_order_source':'Ticket',
            'default_ticket_id': self.id,
            'default_partner_id': self.partner_id.id,
        }
        query=self.env.cr.execute("""Select id from project_task where ticket_id="""+str(self.id))
        result=self.env.cr.fetchall()
        task_list=[each[0] for each in result]
        action['domain'] = [('id','in',task_list)]
        return action
    
class HelpdeskTeams(models.Model):
    _inherit='helpdesk.team'
    
    @api.model
    def create(self,vals):
        result = super(HelpdeskTeams,self).create(vals)
        stages_obj = self.env['helpdesk.stage'].search([])
        for each in stages_obj:
            each.write({'team_ids':[(4, result.id)]})
        return result