from odoo import api, fields, models, _
from odoo.exceptions import UserError

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]
class ApprovalCategory(models.Model):
    _inherit='approval.category'
#     has_project = fields.Selection(CATEGORY_SELECTION, string="Has Project", default="no", required=True)
    has_task = fields.Selection(CATEGORY_SELECTION, string="Has Task", default="no", required=True)

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
#     has_project = fields.Selection(related="category_id.has_project")
    has_task = fields.Selection(related="category_id.has_task")
    project_id = fields.Many2one('project.project', string="Project",related='task_id.project_id',store=True, check_company=True)
    task_id = fields.Many2one('project.task', string="Task / Service Order", domain="['|','|',('assigned_worker_id.user_id','=',request_owner_id),('backfill_engineer_id.user_id','=',request_owner_id),('secondary_backfill_id.user_id','=',request_owner_id)]", check_company=True)