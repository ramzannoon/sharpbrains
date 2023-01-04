from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit='account.move.line'
    work_site_id=fields.Many2one('res.partner','Work Site',domain="[('type','=','work_site'),('parent_id','=',partner_id)]")
    country_id=fields.Many2one('res.country','Country')
    sla_category_id=fields.Many2one('sb.sla.category','SLA Category')
    sla_id=fields.Many2one('sb.sla','SLA',domain="[('sla_category_id','=',sla_category_id)]")