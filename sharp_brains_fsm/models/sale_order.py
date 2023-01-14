from openerp import models, fields, api, exceptions
from odoo import api, fields, models, _
from openerp.exceptions import except_orm
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression

from . import common_methods as comm
from io import BytesIO
from xlutils.copy import copy
from collections import Counter
import base64
from odoo.tools import float_is_zero, float_compare
from functools import partial
from itertools import groupby
try:
    import xlwt
except ImportError:
    xlwt = None

try:
    import xlrd
    from xlrd import *
except ImportError:
    xlrd = None

class SaleOrderLines(models.Model):
    _inherit='sale.order.line'
    sla_category_id=fields.Many2one('sb.sla.category','SLA Category',required=True)
    sla_id=fields.Many2one('sb.sla','SLA',domain="[('sla_category_id','=',sla_category_id)]",required=True)
#     uom=fields.Selection([('Hourly','Hourly'),('Daily','Daily'),('Monthly','Monthly')],'UOM',compute="_cal_pricelist_uom")
    work_site_id=fields.Many2one('res.partner','Work Site',domain="[('type','=','work_site'),('x_end_customer_id','=',order_partner_id)]")
    type=fields.Selection([('Project Based','Project Based'),('On Demand','On Demand')],default='Project Based',related="order_id.type")
    service_order_count = fields.Integer('Service Order Count', compute="_compute_service_order_count")
    sla_category=fields.Char('Category',related='sla_category_id.name')
    
    def _recompute_qty_to_invoice(self, start_date, end_date):
        """ Recompute the qty_to_invoice field for product containing timesheets

            Search the existed timesheets between the given period in parameter.
            Retrieve the unit_amount of this timesheet and then recompute
            the qty_to_invoice for each current product.

            :param start_date: the start date of the period
            :param end_date: the end date of the period
        """
        lines_by_timesheet = self.filtered(lambda sol: sol.product_id and sol.product_id._is_delivered_timesheet())
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        domain = expression.AND([domain, [
            '|',
            ('timesheet_invoice_id', '=', False),
            ('timesheet_invoice_id.state', '=', 'cancel')]])
        if start_date:
            domain = expression.AND([domain, [('date', '>=', start_date)]])
        if end_date:
            domain = expression.AND([domain, [('date', '<=', end_date)]])
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)

        for line in lines_by_timesheet:
            line.qty_to_invoice = mapping.get(line.id, 0.0)
            
    @api.model
    def _nothing_to_invoice_error(self):
        msg = _("""There is nothing to invoice!\n
Reason(s) of this behavior could be:
- You should deliver your products before invoicing them: Click on the "truck" icon (top-right of your screen) and follow instructions.
- You should modify the invoicing policy of your product: Open the product, go to the "Sales tab" and modify invoicing policy from "delivered quantities" to "ordered quantities".
        """)
        return UserError(msg)
    
    def _compute_service_order_count(self):
        for each in self:
            if type(each.id) is int:
                each.service_order_count=0
                query=self.env.cr.execute("""Select id from project_task where sale_line_id="""+str(each.id))
                result=self.env.cr.fetchall()
                each.service_order_count=len(result)
            else:
                each.service_order_count=0
    
    def action_view_service_order(self):        
        action = self.env.ref('project.action_view_all_task').sudo().read()[0]
        query=self.env.cr.execute("""Select id from project_task where sale_line_id="""+str(self.id))
        result=self.env.cr.fetchall()
        task_list=[each[0] for each in result]
        action['domain'] = [('id','in',task_list)]
        return action
    
    def create_task(self):
        if self.order_id.opportunity_id:
            service_order_source='Opportunity'
            opportunity_id=self.order_id.opportunity_id.id
            ticket_id=None
        else:
            service_order_source='Ticket'
            opportunity_id=None
            ticket_id=self.order_id.ticket_id.id
        job_id=self.env['hr.job'].search([('name','=',self.product_id.name)])
        hourly_rate=0
        day_rate=0
        monthly_rate=0
        if self.product_uom.name=='Hours':
            hourly_rate=self.price_unit
        elif self.product_uom.name=='Days':
            day_rate=self.price_unit
        elif self.product_uom.name=='Months':
            monthly_rate=self.price_unit
        values={'task_type':'Service Order',
                'job_id':job_id.id or False,
                'hourly_rate':hourly_rate,
                'day_rate':day_rate,
                'monthly_rate':monthly_rate,
                'project_id':self.order_id.project_id.id,
                'partner_id':self.order_partner_id.id,
                'site_id':self.work_site_id.id,
                'city':self.work_site_id.city,
                'service_order_source':service_order_source,
                'opportunity_id':opportunity_id,
                'ticket_id':ticket_id,
                'name':"/",
                'assigned_worker_id':self.work_site_id.assigned_worker_id.id,
                'backfill_engineer_id':self.work_site_id.backfill_engineer_id.id,
                'secondary_backfill_id':self.work_site_id.secondary_backfill_id.id,
                'sale_order_id':self.order_id.id,
                'sale_line_id':self.id,
                'sla':self.sla_id.id
                
                }
        task = self.env['project.task'].sudo().create(values)
        if self.sla_category!='Full Time':
            task.write({'name':str(task.number)+":"+str(self.order_id.project_id.name)})
        elif self.sla_category=='Full Time':
            task.write({'name':"FTE Attendance:"+str(self.order_id.project_id.name)+"("+str(task.number)+")",
                        'fte_attendance':True})
        self.write({'task_id': task.id})
        # post message on task
        task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.order_id.id, self.order_id.name, self.product_id.name)
        task.message_post(body=task_msg)
        return task
    
    def _timesheet_create_project(self):
        if not self.order_id.project_id:
            project = super()._timesheet_create_project()
            project.write({'allow_timesheets': True,
                           'project_type':'Customer Project',
                           'sale_order_id':self.order_id.id,
                           'sale_line_id':self.id,
                           'bill_type':'customer_project',
                           'allow_billable':True
                           })
        else:
            project=self.order_id.project_id
            project.write({'allow_timesheets': True,
                           'project_type':'Customer Project',
                           'sale_order_id':self.order_id.id,
                           'sale_line_id':self.id,
                           'bill_type':'customer_project',
                           'allow_billable':True
                           })
        self.order_id.write({'project_id':project.id})
        if self.order_id.opportunity_id:
            self.order_id.opportunity_id.write({'project_id':project.id})
        return project
    def _timesheet_create_task(self, project):
        """ Generate task for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        if self.order_id.project_id:
            self.order_id.project_id.write({'allow_timesheets': True,
                           'project_type':'Customer Project',
                           'sale_order_id':self.order_id.id,
                           'sale_line_id':self.id,
                           'bill_type':'customer_project',
                           'allow_billable':True,
#                            'type':self.order_id.project_type
                           })
        if self.order_id.type=='On Demand':
            if self.sla_category!='Full Time':
                values = self._timesheet_create_task_prepare_values(project)
                task = self.env['project.task'].sudo().create(values)
                job_id=self.env['hr.job'].search([('name','=',self.product_id.name)])
    #             job_list=[]
    #             for line in self.project_id.sale_order_id.order_line:
    #                 job_obj=self.env['hr.job'].search([('name','=',line.product_id.name)])
    #                 if job_obj:
    #                     job_list.append(job_obj.id)
    #             self.write({'job_ids':[(6,0,job_list)]})
                if self.order_id.opportunity_id:
                    service_order_source='Opportunity'
                    opportunity_id=self.order_id.opportunity_id.id
                    ticket_id=None
                else:
                    service_order_source='Ticket'
                    opportunity_id=None
                    ticket_id=self.order_id.ticket_id.id
                hourly_rate=0
                day_rate=0
                monthly_rate=0
                if self.product_uom.name=='Hours':
                    hourly_rate=self.price_unit
                elif self.product_uom.name=='Days':
                    day_rate=self.price_unit
                elif self.product_uom.name=='Months':
                    monthly_rate=self.price_unit
                task.write({'task_type':'Service Order',
                            'job_id':job_id.id or False,
                            'hourly_rate':hourly_rate,
                            'day_rate':day_rate,
                            'monthly_rate':monthly_rate,
                            'project_id':self.order_id.project_id.id,
                            'partner_id':self.order_partner_id.id,
                            'site_id':self.work_site_id.id,
                            'city':self.work_site_id.city,
                            'service_order_source':service_order_source,
                            'opportunity_id':opportunity_id,
                            'ticket_id':ticket_id,
                            'name':str(task.number)+":"+str(self.order_id.project_id.name),
                            'assigned_worker_id':self.work_site_id.assigned_worker_id.id,
                            'backfill_engineer_id':self.work_site_id.backfill_engineer_id.id,
                            'secondary_backfill_id':self.work_site_id.secondary_backfill_id.id,
                            'sale_order_id':self.order_id.id,
                            'sla':self.sla_id.id})
                self.write({'task_id': task.id,})
                # post message on task
                task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.order_id.id, self.order_id.name, self.product_id.name)
                task.message_post(body=task_msg)
                return task
        if self.sla_category=='Full Time':
            values = self._timesheet_create_task_prepare_values(project)
            task = self.env['project.task'].sudo().create(values)
            job_id=self.env['hr.job'].search([('name','=',self.product_id.name)])
#             job_list=[]
#             for line in self.project_id.sale_order_id.order_line:
#                 job_obj=self.env['hr.job'].search([('name','=',line.product_id.name)])
#                 if job_obj:
#                     job_list.append(job_obj.id)
#             self.write({'job_ids':[(6,0,job_list)]})
            if self.order_id.opportunity_id:
                service_order_source='Opportunity'
                opportunity_id=self.order_id.opportunity_id.id
                ticket_id=None
            else:
                service_order_source='Ticket'
                opportunity_id=None
                ticket_id=self.order_id.ticket_id.id
            hourly_rate=0
            day_rate=0
            monthly_rate=0
            if self.product_uom.name=='Hours':
                hourly_rate=self.price_unit
            elif self.product_uom.name=='Days':
                day_rate=self.price_unit
            elif self.product_uom.name=='Months':
                monthly_rate=self.price_unit
                
            task.write({'task_type':'Service Order',
                        'job_id':job_id.id or False,
                        'hourly_rate':hourly_rate,
                        'day_rate':day_rate,
                        'monthly_rate':monthly_rate,
                        'project_id':self.order_id.project_id.id,
                        'partner_id':self.order_partner_id.id,
                        'site_id':self.work_site_id.id,
                        'city':self.work_site_id.city,
                        'service_order_source':service_order_source,
                        'opportunity_id':opportunity_id,
                        'ticket_id':ticket_id,
                        'name':"FTE Attendance:"+str(self.order_id.project_id.name)+" ("+str(task.number)+")",
                        'assigned_worker_id':self.work_site_id.assigned_worker_id.id,
                        'backfill_engineer_id':self.work_site_id.backfill_engineer_id.id,
                        'secondary_backfill_id':self.work_site_id.secondary_backfill_id.id,
                        'sale_order_id':self.order_id.id,
                        'fte_attendance':True,
                        'sla':self.sla_id.id})
            self.write({'task_id': task.id})
            # post message on task
            task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.order_id.id, self.order_id.name, self.product_id.name)
            task.message_post(body=task_msg)
            return task
            
    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
            Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
            new project/task. This explains the searches on 'sale_line_id' on project/task. This also
            implied if so line of generated task has been modified, we may regenerate it.
        """
        so_line_task_global_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking == 'task_global_project')
        so_line_new_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking in ['project_only', 'task_in_project'])

        # search so lines from SO of current so lines having their project generated, in order to check if the current one can
        # create its own project, or reuse the one of its order.
        map_so_project = {}
        if so_line_new_project:
            order_ids = self.mapped('order_id').ids
            so_lines_with_project = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '=', False)])
            map_so_project = {sol.order_id.id: sol.project_id for sol in so_lines_with_project}
            so_lines_with_project_templates = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '!=', False)])
            map_so_project_templates = {(sol.order_id.id, sol.product_id.project_template_id.id): sol.project_id for sol in so_lines_with_project_templates}

        # search the global project of current SO lines, in which create their task
        map_sol_project = {}
        if so_line_task_global_project:
            map_sol_project = {sol.id: sol.product_id.with_company(sol.company_id).project_id for sol in so_line_task_global_project}

        def _can_create_project(sol):
            if not sol.project_id:
                if sol.product_id.project_template_id:
                    return (sol.order_id.id, sol.product_id.project_template_id.id) not in map_so_project_templates
                elif sol.order_id.id not in map_so_project:
                    return True
            return False

        def _determine_project(so_line):
            """Determine the project for this sale order line.
            Rules are different based on the service_tracking:

            - 'project_only': the project_id can only come from the sale order line itself
            - 'task_in_project': the project_id comes from the sale order line only if no project_id was configured
              on the parent sale order"""
            if so_line.order_id.project_id:
                return so_line.order_id.project_id
            elif so_line.product_id.service_tracking == 'project_only':
                return so_line.project_id
            elif so_line.product_id.service_tracking == 'task_in_project':
                return so_line.order_id.project_id or so_line.project_id

            return False

        # task_global_project: create task in global project
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                if map_sol_project.get(so_line.id):
                    so_line._timesheet_create_task(project=map_sol_project[so_line.id])

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project:
            project = _determine_project(so_line)
            if not project and _can_create_project(so_line):
                project = so_line._timesheet_create_project()
                if so_line.product_id.project_template_id:
                    map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)] = project
                else:
                    map_so_project[so_line.order_id.id] = project
            elif not project:
                # Attach subsequent SO lines to the created project
                so_line.project_id = (
                    map_so_project_templates.get((so_line.order_id.id, so_line.product_id.project_template_id.id))
                    or map_so_project.get(so_line.order_id.id)
                )
            if so_line.product_id.service_tracking == 'task_in_project':
                if not project:
                    if so_line.product_id.project_template_id:
                        project = map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)]
                    else:
                        project = map_so_project[so_line.order_id.id]
                if not so_line.task_id:
                    so_line._timesheet_create_task(project=project)
                    
#     @api.onchange('sla_category_id','sla_id')
#     def cal_unit_price(self):
#         if self.product_id and self.sla_category_id and self.sla_id and self.work_site_id:
#             price_list=self.env['product.template.pricelist'].search([('product_id','=',self.product_id.product_tmpl_id.id),('country_id','=',self.work_site_id.country_id.id),('city_id','=',self.work_site_id.city_id.id),('sla_id','=',self.sla_id.id),('sla_category_id','=',self.sla_category_id.id)])
#             if price_list:
#                 self.price_unit=price_list.rate
#             else:
#                 self.price_unit=self.product_id.product_tmpl_id.lst_price
    
#     @api.depends('product_id','sla_category_id','sla_id','work_site_id')
#     def _cal_pricelist_uom(self):
#         for each in self:
#             if each.product_id and each.sla_category_id and each.sla_id and each.work_site_id:
#                 price_list=self.env['product.template.pricelist'].search([('product_id','=',each.product_id.product_tmpl_id.id),('country_id','=',each.work_site_id.country_id.id),('city_id','=',each.work_site_id.city_id.id),('sla_id','=',each.sla_id.id),('sla_category_id','=',each.sla_category_id.id)])
#                 if price_list:
#                     each.uom=price_list.uom
#                 else:
#                     each.uom=None
#             else:
#                 each.uom=None
    def _create_invoices(self, grouped=False, final=False, start_date=None, end_date=None):
#         moves = super(SaleOrder, self)._create_invoices(grouped, final)
#         moves._link_timesheets_to_invoice(start_date, end_date)
#         return moves
#     def _create_invoices(self, grouped=False, final=False, date=None):
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order_line in self:
            order = order_line.order_id
            current_section_vals = None
            down_payments = order_line

            invoice_vals = order_line._prepare_invoice_multi()
            invoiceable_lines = order_line._get_invoiceable_lines_multi(final)
            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                    print (line.qty_to_invoice)
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line_multi(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys])
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list
            
            if len(invoice_vals_list) < len(self):
                SaleOrderLine = self.env['sale.order.line']
                for invoice in invoice_vals_list:
                    sequence = 1
                    for line in invoice['invoice_line_ids']:
                        line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                        sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
            moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)
        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
#             if final:
#                 moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
            for move in moves:
                move.message_post_with_view('mail.message_origin_link',
                    values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                    subtype_id=self.env.ref('mail.mt_note').id
                )
            return moves
    def _get_invoice_grouping_keys(self):
        return ['company_id', 'partner_id', 'currency_id']
    def _get_invoiceable_lines_multi(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)

        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)
    def _prepare_invoice_line_multi(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'analytic_account_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
            'work_site_id':self.work_site_id.id,
            'country_id':self.country_id.id,
            'sla_category_id':self.sla_category_id.id,
            'sla_id':self.sla_id.id,
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res
    def _prepare_invoice_multi(self):
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.order_id.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.order_id.note,
            'currency_id': self.order_id.pricelist_id.currency_id.id,
            'campaign_id': self.order_id.campaign_id.id,
            'medium_id': self.order_id.medium_id.id,
            'source_id': self.order_id.source_id.id,
            'user_id': self.order_id.user_id.id,
            'invoice_user_id': self.order_id.user_id.id,
            'team_id': self.order_id.team_id.id,
            'partner_id': self.order_id.partner_invoice_id.id,
            'partner_shipping_id': self.order_id.partner_shipping_id.id,
            'fiscal_position_id': (self.order_id.fiscal_position_id or self.order_id.fiscal_position_id.get_fiscal_position(self.order_id.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.order_id.name,
            'invoice_payment_term_id': self.order_id.payment_term_id.id,
            'payment_reference': self.order_id.reference,
            'transaction_ids': [(6, 0, self.order_id.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals
    
    def _prepare_invoice_line(self, **optional_values):
        invoice_line = super(SaleOrderLines, self)._prepare_invoice_line(**optional_values)
        invoice_line['work_site_id'] = self.work_site_id.id
        invoice_line['country_id'] = self.work_site_id.country_id.id
        invoice_line['sla_category_id'] = self.sla_category_id.id
        invoice_line['sla_id'] = self.sla_id.id
        return invoice_line
        
class SaleOrder(models.Model):
    _inherit='sale.order'
    city_id=fields.Many2one('res.city','City',related='partner_id.city_id')
    state_id=fields.Many2one('res.country.state','State',related='partner_id.state_id')
    country_id=fields.Many2one('res.country','Country',related='partner_id.country_id')
    type=fields.Selection([('Project Based','Project Based'),('On Demand','On Demand')],default='Project Based',required=True)
    ticket_id=fields.Many2one('helpdesk.ticket','Ticket')
    product_id=fields.Many2one('product.product','Work Type',domain="[('product_tmpl_id.type','=','service')]")
    partner_invoice_id=fields.Many2one(domain="[('customer_rank','!=',0),('type','=','contact')]")
    project_id=fields.Many2one('project.project','Project',domain="['|',('partner_id','=',partner_invoice_id),('misc_project','=',True)]")
    visible_project=fields.Boolean(default=True)
#     def _create_invoices(self, grouped=False, final=False, start_date=None, end_date=None):
#         """ Override the _create_invoice method in sale.order model in sale module
#             Add new parameter in this method, to invoice sale.order with a date. This date is used in sale_make_invoice_advance_inv into this module.
#             :param start_date: the start date of the period
#             :param end_date: the end date of the period
#             :return {account.move}: the invoices created
#         """
#         moves = super(SaleOrder, self)._create_invoices(grouped, final)
#         moves._link_timesheets_to_invoice(start_date, end_date)
#         return moves
# class Product(models.Model):
#     _inherit="product.template"
#     product_price_list=fields.One2many('product.template.pricelist','product_id','Price List')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        - Sales Team
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return

        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
#             'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.context.get('default_user_id', self.env.uid)
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        if not self.env.context.get('not_self_saleperson') or not self.team_id:
            values['team_id'] = self.env['crm.team'].with_context(
                default_team_id=self.partner_id.team_id.id
            )._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], user_id=user_id)
        self.update(values)

class SLA(models.Model):
    _name='sb.sla'
    name=fields.Char('Name')
    sla_category_id=fields.Many2one('sb.sla.category','SLA Category')

class SLACategory(models.Model):
    _name='sb.sla.category'
    name=fields.Char('Name')

class Product_Pricelist(models.Model):
    _name='product.template.pricelist'
#     country_id=fields.Many2one('res.country','Country',required=True)
#     state_id=fields.Many2one('res.country.state','State/County',required=True,domain="[('country_id','=',country_id)]")
#     city_id=fields.Many2one('res.city','City',required=True,domain="[('country_id','=',country_id),('state_id','=',state_id)]")
#     sla_category_id=fields.Many2one('sb.sla.category','SLA Category',required=True)
#     sla_id=fields.Many2one('sb.sla','SLA',domain="[('sla_category_id','=',sla_category_id)]",required=True)
#     uom=fields.Selection([('Hourly','Hourly'),('Daily','Daily'),('Monthly','Monthly')],'UOM',required=True)
#     rate=fields.Float('Rate',required=True)
#     product_id=fields.Many2one('product.template','Product')
#     
#     _sql_constraints = [
#     ('pricelist_unique', 'unique (prodcut_id,country_id,city_id,sla_category,sla_type,uom)',
#         'Price List should be unique!')
#     ]
#     
#     @api.onchange('country_id')
#     def onchange_country(self):
#         self.state_id=False
#         self.city_id=False
#     
#     @api.onchange('state_id')
#     def onchange_state(self):
#         self.city_id=False
#     
#     
#     @api.onchange('sla_category_id')
#     def onchange_sla_category(self):
#         self.sla_id=False
#    

class SbQuotationImportErrorLog(models.TransientModel):

    _name = 'sb.quotation.import.error_log'
    _order = 'seq'

    so_import_id = fields.Many2one('sb.quotation.import', string="Import Id")
    cell = fields.Char(string="Excel Cell #")
    msg = fields.Char(string="Message")
    seq = fields.Integer(string="Seq")
    reason = fields.Text(string="Reason")
    
class SbQuotationImport(models.TransientModel):
    _name = 'sb.quotation.import'

    sale_order_id=fields.Many2one('sale.order','Sale Order',required=True)

    valid = fields.Boolean(string='Valid', default=False)
    message = fields.Text(string='Message')
    error_log = fields.One2many('sb.quotation.import.error_log', 'so_import_id', string='Error Log')
    import_attachment = fields.Binary(string='Upload Excel File')
    import_attachment_name = fields.Char(string='Upload Excel File')


    def download_template(self):
        file_name = "Import_Quotation"
        try:
            return self.export_temp_xl(file_name)
        except Exception as e:
            raise Exception('Error!!!', e)

    def export_temp_xl(self, file_name):
        row, col = comm.row, comm.col
        workbook, worksheet = comm.prepare_worksheet(self, 'Quotation Import', 'Quotation Import', 8, 2)
        worksheet.write(row + 3, col, 'Country', comm.style1)  #
        worksheet.col(col).width = 250 * int(comm.col_width)

        worksheet.write(row + 3, col + 1, 'City', comm.style1)  #
        worksheet.col(col + 1).width = 150 * int(comm.col_width_2)
        worksheet.col(col + 1).set_style(comm.style_for_str)

        worksheet.write_merge(row + 2,row + 2,col + 2,col + 4,'Dispatch', comm.style1)  #
        worksheet.col(col + 2).width = 150 * int(comm.col_width_2)
        worksheet.col(col + 2).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 2, 'SBD 4H Response', comm.style1)  #
        worksheet.col(col + 2).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 2).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 3, 'NBD (1 Hour TOT)', comm.style1)  #
        worksheet.col(col + 3).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 3).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 4, 'T&M Hourly Pricing', comm.style1)  #
        worksheet.col(col + 4).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 4).set_style(comm.style_for_str)
        
#         worksheet.write(row + 2, col + 2, 'Dispatch', comm.style1)  #
#         worksheet.col(col + 2).width = 256 * int(comm.col_width_2)
#         worksheet.col(col + 2).set_style(comm.style_for_str)
#         
#         worksheet.write(row + 2, col + 2, 'Dispatch', comm.style1)  #
#         worksheet.col(col + 2).width = 256 * int(comm.col_width_2)
#         worksheet.col(col + 2).set_style(comm.style_for_str)
        
        worksheet.write_merge(row + 2, row + 2, col + 5,col + 6, 'All Model (Depot/Backfill/SV)', comm.style1)  #
        worksheet.col(col + 5).width = 256 * int(comm.col_width_2)
        worksheet.col(col + 5).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 5, 'Half Day', comm.style1)  #
        worksheet.col(col + 5).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 5).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 6, 'Full Day', comm.style1)  #
        worksheet.col(col + 6).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 6).set_style(comm.style_for_str)
        
        worksheet.write(row + 2, col + 7, 'Full Time', comm.style1)  #
        worksheet.col(col + 7).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 7).set_style(comm.style_for_str)
        
        worksheet.write(row + 3, col + 7, 'Monthly Rate', comm.style1)  #
        worksheet.col(col + 7).width = 100 * int(comm.col_width_2)
        worksheet.col(col + 7).set_style(comm.style_for_str)

        worksheet.write(row + 2, col + 9, 'Country', comm.style1)  #
        worksheet.col(col + 9).width = 250 * int(comm.col_width_2)
        a = row + 3

        worksheet.write(row + 2, col + 10, 'City', comm.style1)  #
        worksheet.col(col + 10).width = 250* int(comm.col_width_2)
        b = row + 3
        
        country_obj=self.env['res.country'].search([])
        for country in country_obj:
            worksheet.write(a, col + 9, country.name)            
            city_obj=self.env['res.city'].search([('country_id','=',country.id)])
            for city in city_obj:
                worksheet.write(b, col + 10, city.name)
                b = b + 1
                a = a + 1
            if not city_obj:
                b = b + 1
                a = a + 1
            
        io_stream = BytesIO()
        workbook.save(io_stream)
        io_stream.seek(0)
        file_data = io_stream.read()
        io_stream.close()

        rb = None
        rb = xlrd.open_workbook(file_contents=file_data, formatting_info=True)
        w_workbook = copy(rb)

        fp = BytesIO()
        w_workbook.save(fp)
        fp.seek(0)
        modified_file_data = fp.read()
        fp.close()
        modified_data = base64.encodestring(modified_file_data)
        file_type = "xls"
        attach_vals = {
            'name': '%s.%s' % (file_name, file_type),
            'db_datas': modified_data,
            'store_fname': '%s.%s' % (file_name, file_type),
        }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/report/download_report?model=ir.attachment&field=datas&id=%s&filename=%s.%s' % (
                doc_id.id, file_name, file_type),
            'target': 'new',
        }



    def validate(self):
        try:
            def default(o):
                if isinstance(o, (datetime.date, datetime.datetime)):
                    return o.isoformat()

            self.error_log.unlink()
            self.ensure_one()
            master_list = []
            self.validate_template(self.import_attachment, 'upload',master_list)
            if not master_list:
                self.valid = False
                self.message = "Please attach file first and then proceed."
            wizard_form = self.env.ref('sharp_brains.view_sb_quotation_import_form', False)
            ctx = self._context.copy()
            ctx.update({'master_data_list': master_list})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sb.quotation.import',
                'name': _('Quotation Import'),
                'res_id': self.id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': wizard_form.id,
                'target': 'new',
                'context': ctx
            }
        except Exception as e:
            raise Exception("Error!!!", e)



    def validate_template(self, data,type, master_list):
        if data:
            rb = None
            rb = xlrd.open_workbook(file_contents=base64.decodestring(data), formatting_info=False)
            error = "Uploading template is wrong please first download the template insert data into it and then try to upload it again thanks"
            r_sheet = None
            try:
                r_sheet = rb.sheet_by_name('Quotation Import')  # read only copy to introspect the file
                sheet_names = rb.sheet_names()
                if len(sheet_names) > 1:
                    raise exceptions
            except Exception:
                raise ValidationError(error)
            country_col = 2
            city_col = 3
            dispatch_sbd_col = 4
            dispatch_nbd_col = 5
            dispatch_tm_col = 6
            all_half_col = 7
            all_full_col = 8
            fte_col = 9
            

            successful = True
            data_list = []
            error_list = []
            arr_cnic = []
            arr_work = []
            # cell_val = r_sheet.cell(row, col).value
            from datetime import datetime
            for row in range(4, r_sheet.nrows):
            # for row in range(3, 4):
                #                 successful=True
                tot_col = 9
                starting_col = 2
                count_empty = starting_col
                for col in range(starting_col, tot_col):
                    """/ Checking for Empty Row"""
                    cell_val = r_sheet.cell(row, col).value
                    if cell_val == '':
                        count_empty += 1
                if count_empty == 9:
                    break

                obj = {}


                obj.update({'sale_order_id': self.sale_order_id.id})

                country = r_sheet.cell(row, country_col).value
                if country == '':
                    successful = False
                    error_list.append((0, 0, {'cell': xlrd.cellname(row, country_col),
                                              'msg': "Empty Value!!!",
                                              'seq': row,
                                              'reason': " 'Country' field is mandatory, thus could not be left empty."}))
                country_obj=self.env['res.country'].search([])
                country_list=[]
                for each in country_obj:
                    country_list.append(each.name)
                if country not in country_list:
                    successful = False
                    error_list.append((0, 0, {'cell': xlrd.cellname(row, country_col),
                                              'msg': "Empty Value!!!",
                                              'seq': row,
                                              'reason': "Spelling or upper/lower case mistake. Valid values are (%s) " % country_list}))

                else:
                    country_obj=self.env['res.country'].search([('name','=',country)])
                    obj.update({'country_id': country_obj.id})
                
                city = r_sheet.cell(row, city_col).value
                if city == '':
                    successful = False
                    error_list.append((0, 0, {'cell': xlrd.cellname(row, city_col),
                                              'msg': "Empty Value!!!",
                                              'seq': row,
                                              'reason': " 'City' field is mandatory, thus could not be left empty."}))
                if country:
                    city_obj=self.env['res.city'].search([('country_id','=',country_obj.id),('name','=',city)])
                    city_list=[]
                    for each in city_obj:
                        city_list.append(each.name)
                    if city not in city_list:
                        successful = False
                        error_list.append((0, 0, {'cell': xlrd.cellname(row, city_col),
                                                  'msg': "Empty Value!!!",
                                                  'seq': row,
                                                  'reason': "Spelling or upper/lower case mistake. Valid values are (%s) " % city_list}))
    
                    else:
                        city_obj=self.env['res.city'].search([('name','=',city)])
                        obj.update({'city_id': city_obj.id})
                
                dispatch_sbd_rate = r_sheet.cell(row, dispatch_sbd_col).value
#                 if type(dispatch_sbd_rate) is not int and not type(dispatch_sbd_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, dispatch_sbd_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'dispatch_sbd_rate': dispatch_sbd_rate})
                
                dispatch_nbd_rate = r_sheet.cell(row, dispatch_nbd_col).value
#                 if type(dispatch_nbd_rate) is not int and type(dispatch_nbd_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, dispatch_nbd_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'dispatch_nbd_rate': dispatch_nbd_rate})
                    
                dispatch_tm_rate = r_sheet.cell(row, dispatch_tm_col).value
#                 if type(dispatch_tm_rate) is not int and type(dispatch_tm_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, dispatch_tm_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'dispatch_tm_rate': dispatch_tm_rate})
                    
                all_half_rate = r_sheet.cell(row, all_half_col).value
#                 if type(all_half_rate) is not int and type(all_half_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, all_half_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'all_half_rate': all_half_rate})
                    
                all_full_rate = r_sheet.cell(row, all_full_col).value
#                 if type(all_full_rate) is not int and type(all_full_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, all_full_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'all_full_rate': all_full_rate})
                
                fte_rate = r_sheet.cell(row, fte_col).value
#                 if type(fte_rate) is not int and type(fte_rate) is not float :
#                     successful = False
#                     error_list.append((0, 0, {'cell': xlrd.cellname(row, fte_col),
#                                               'msg': "Invalid Value!!!",
#                                               'seq': row,
#                                               'reason': "Value should be integer or float (%s) "}))
# 
#                 else:
                obj.update({'fte_rate': fte_rate})
                

                data_list.append(obj)
            if successful:
                self.valid = True
                self.write({'message': 'Everything seems valid.'})
                #                 self.master_data_list.append(data_list)
                try:
                    # self.master_data_list=data_list
                    master_list.extend(data_list)
                    pass
                except Exception as e:
                    raise ValidationError(e)



            else:
                self.error_log = []
                self.write({
                    'message': 'Current operation cannot succeeded! for more information please follow the error log.'})
                self.error_log = error_list
        else:
            self.write({'message': 'Please attach file first and then proceed.'})



    def confirm(self):
        master_list = self._context.get('master_data_list')
        if master_list:
            try:
                for std_rec in master_list:
                    order_lines=[(5,0,0)]
                    dispatch_sbd_vals=[]
                    dispatch_nbd_vals=[]
                    dispatch_tm_vals=[]
                    all_hd_vals=[]
                    all_fd_vals=[]
                    ft_mr_vals=[]
                    sale_order_obj=self.env['sale.order'].search([('id','=',std_rec['sale_order_id'])])
                    worksite_obj=self.env['res.partner'].search([('x_end_customer_id','=',sale_order_obj.partner_id.id),('type','=','work_site'),('country_id','=',std_rec['country_id']),('city_id','=',std_rec['city_id'])])
                    if not worksite_obj:
                        raise ValidationError("""Customer's worksite not created, plz create worksite to procced.""")
                    dispatch_obj=self.env['sb.sla.category'].search([('name','=','Dispatch')])
                    if not dispatch_obj:
                        raise ValidationError('Dispatch SLA Category not configured.')
                    
                    dispatch_sbd_obj=self.env['sb.sla'].search([('name','=','SBD 4H Response')])
                    if not dispatch_sbd_obj:
                        raise ValidationError('SBD 4H Response SLA of Dispatch Category not configured.')
                    if dispatch_obj and dispatch_sbd_obj and std_rec['dispatch_sbd_rate']:
                        
                        dispatch_sbd_vals={'product_id':sale_order_obj.product_id.id,
                                           'name':sale_order_obj.product_id.name,
                                           'work_site_id':worksite_obj.id,
                                           'sla_category_id':dispatch_obj.id,
                                           'sla_id':dispatch_sbd_obj.id,
                                           'price_unit':std_rec['dispatch_sbd_rate'],
                                           'qty_delivered_method':'timesheet',
                                           'project_id':sale_order_obj.project_id.id,
                                           'order_id':sale_order_obj.id,
                                          }
#                         order_lines.append((0,0,dispatch_sbd_vals))
#                         sale_order_obj=dispatch_sbd_vals
                        self.env['sale.order.line'].create(dispatch_sbd_vals)
                    
                    dispatch_nbd_obj=self.env['sb.sla'].search([('name','=','NBD (1 Hour TOT)')])
                    if not dispatch_nbd_obj:
                        raise ValidationError('NBD (1 Hour TOT) SLA of Dispatch Category not configured.')
                    
                    if dispatch_obj and dispatch_nbd_obj and std_rec['dispatch_nbd_rate']:
                        
                        dispatch_nbd_vals={'product_id':sale_order_obj.product_id.id,
                          'work_site_id':worksite_obj.id,
                          'sla_category_id':dispatch_obj.id,
                          'sla_id':dispatch_nbd_obj.id,
                          'price_unit':std_rec['dispatch_nbd_rate'],
                          'qty_delivered_method':'timesheet',
                          'project_id':sale_order_obj.project_id.id,
                          'order_id':sale_order_obj.id,
                          }
#                         order_lines.append((0,0,dispatch_nbd_vals))
#                         sale_order_obj=dispatch_nbd_vals
                        self.env['sale.order.line'].create(dispatch_nbd_vals)
                    
                    dispatch_tm_obj=self.env['sb.sla'].search([('name','=','T&M Hourly Pricing')])
                    if not dispatch_tm_obj:
                        raise ValidationError('T&M Hourly Pricing of Dispatch Category not configured.')
                    
                    if dispatch_obj and dispatch_tm_obj and std_rec['dispatch_nbd_rate']:
                        dispatch_tm_vals={'product_id':sale_order_obj.product_id.id,
                          'work_site_id':worksite_obj.id,
                          'sla_category_id':dispatch_obj.id,
                          'sla_id':dispatch_tm_obj.id,
                          'price_unit':std_rec['dispatch_tm_rate'],
                          'qty_delivered_method':'timesheet',
                          'project_id':sale_order_obj.project_id.id,
                          'order_id':sale_order_obj.id,
                          }
#                         order_lines.append((0,0,dispatch_tm_vals))
                        self.env['sale.order.line'].create(dispatch_tm_vals)
                        
                    
                    all_obj=self.env['sb.sla.category'].search([('name','=','All Model (Depot/Backfill/SV)')])
                    if not all_obj:
                        raise ValidationError('All Model (Depot/Backfill/SV) SLA Category not configured.')
                    all_hd_obj=self.env['sb.sla'].search([('name','=','Half Day')])
                    if not all_hd_obj:
                        raise ValidationError('Half Day of All Model (Depot/Backfill/SV) Category not configured.')
                    
                    if all_obj and all_hd_obj and std_rec['all_half_rate']:
                        all_hd_vals={'product_id':sale_order_obj.product_id.id,
                          'work_site_id':worksite_obj.id,
                          'sla_category_id':all_obj.id,
                          'sla_id':all_hd_obj.id,
                          'price_unit':std_rec['all_half_rate'],
                          'qty_delivered_method':'timesheet',
                          'project_id':sale_order_obj.project_id.id,
                          'order_id':sale_order_obj.id,
                          }
#                         order_lines.append((0,0,all_hd_vals))
                        self.env['sale.order.line'].create(all_hd_vals)
                        
                    all_fd_obj=self.env['sb.sla'].search([('name','=','Full Day')])
                    if not all_fd_obj:
                        raise ValidationError('Full Day of All Model (Depot/Backfill/SV) Category not configured.')
                    
                    if all_obj and all_fd_obj and std_rec['all_full_rate']:
                        all_fd_vals={'product_id':sale_order_obj.product_id.id,
                          'work_site_id':worksite_obj.id,
                          'sla_category_id':all_obj.id,
                          'sla_id':all_fd_obj.id,
                          'price_unit':std_rec['all_full_rate'],
                          'qty_delivered_method':'timesheet',
                          'project_id':sale_order_obj.project_id.id,
                          'order_id':sale_order_obj.id,
                          }
#                         order_lines.append((0,0,all_fd_vals))
                        self.env['sale.order.line'].create(all_fd_vals)
                    fulltime_obj=self.env['sb.sla.category'].search([('name','=','Full Time')])
                    if not fulltime_obj:
                        raise ValidationError('Full Time SLA Category not configured.')
                    
                    ft_mr_obj=self.env['sb.sla'].search([('name','=','Monthly Rate')])
                    if not ft_mr_obj:
                        raise ValidationError('Monthly Rate of Full Time Category not configured.')
                    if fulltime_obj and ft_mr_obj and std_rec['fte_rate']:
                        ft_mr_vals={'product_id':sale_order_obj.product_id.id,
                          'work_site_id':worksite_obj.id,
                          'sla_category_id':fulltime_obj.id,
                          'sla_id':ft_mr_obj.id,
                          'price_unit':std_rec['fte_rate'],
                          'qty_delivered_method':'timesheet',
                          'project_id':sale_order_obj.project_id.id,
                          'order_id':sale_order_obj.id,
                          }
#                         order_lines.append((0,0,ft_mr_vals))
#                     sale_order_obj.order_line=list
                        self.env['sale.order.line'].create(ft_mr_vals)
            except Exception as ex:
                raise ValidationError(ex)
        else:
            raise ValidationError("Empty File!!! Please insert data into the file or refresh your browser and try again.")

        self.message = "Quotation has been imported successfully."
        master_list = []
        # self.master_data_list = []
        self.valid = False
        import_form = self.env.ref('sharp_brains.view_sb_quotation_import_form', False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sb.quotation.import',
            'name': _('Quotation Import'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': import_form.id,
            'target': 'new',
            'context': self._context

        }

    def reset_import_form(self):
        import_form = self.env.ref('sharp_brains.view_sb_quotation_import_form', False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sb.quotation.import',
            'name': _('Quotation Import'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': import_form.id,
            'target': 'new',
            'context': self._context
        }

    @api.onchange('type')
    def onchange_type(self):
        self.job_id = False
        lst = []
        if self.type:
            for type in self.env['hr.job'].search([]):
                if self.type in type.type_ids:
                    lst.append(type.id)
        return {'domain': {'job_id': [('id', 'in', lst)]}}

    @api.onchange('job_id')
    def onchange_designation(self):
        return self.with_context({'signal': 'call_from_desination', 'current_object': self}).onchange_type()

    @api.onchange('type', 'employee_type')
    def onchange_type(self):
        print('here')
        if self._context.get('signal', False) != 'call_from_desination':
            self.job_id = ''
        if self._context.get('current_object', False):
            self = self._context.get('current_object')

        lst = []
        if self.type:
            for job in self.env['hr.job'].search([]):
                if self.type in job.type_ids:
                    lst.append(job.id)
        return {'domain': {'job_id': [('id', 'in', lst)]}}

    @api.onchange('department_id')
    def onchange_department(self):
        self.project_id = False
        lst = []
        if self.department_id:
            for project in self.env['project.project'].search([]):
                if self.department_id.id == project.department_id.id:
                    if project.system_generated == True:
                        self.project_id = project.id
                    lst.append(project.id)
        return {'domain': {'project_id': [('id', 'in', lst)]}}

    @api.onchange('job_id')
    def GetEmployeeScale(self):
        if self.job_id:
            self.employee_scale = self.job_id.scale_id.id

    @api.onchange('job_id', 'type_id')
    def Get_Scale(self):
        if self.scale_apply == False:
            self.employee_scale = self.job_id.scale_id.id
            
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    invoice_policy=fields.Selection([('Single Invoice','Single Invoice'),('Multi Invoice','Multi Invoice')],'Invoice Policy',required=True,default='Single Invoice')
    
    def create_invoices(self):
        """ Override method from sale/wizard/sale_make_invoice_advance.py

            When the user want to invoice the timesheets to the SO
            up to a specific period then we need to recompute the
            qty_to_invoice for each product_id in sale.order.line,
            before creating the invoice.
        """
        sale_orders = self.env['sale.order'].browse(
                self._context.get('active_ids', [])
            )
        if self.invoice_policy=='Single Invoice':
            
            if self.advance_payment_method == 'delivered' and self.invoicing_timesheet_enabled:
                if self.date_start_invoice_timesheet or self.date_end_invoice_timesheet:
                    sale_orders.mapped('order_line')._recompute_qty_to_invoice(self.date_start_invoice_timesheet, self.date_end_invoice_timesheet)
    
                invoice=sale_orders._create_invoices(final=self.deduct_down_payments, start_date=self.date_start_invoice_timesheet, end_date=self.date_end_invoice_timesheet)
                approvals=self.env['approval.request'].search([('task_id.sale_order_id','in',sale_orders.ids),('request_status','=','approved'),'|',('date','>=',self.date_start_invoice_timesheet),('date','<=',self.date_end_invoice_timesheet)])
                move_lines = []
    #             for rec in approvals:
                sum_of_stock = 0
                sum_of_client = 0
                fte_overtime = approvals.filtered(lambda x: x.category_id.name in ('FTE Overtime'))
                fte_expense = approvals.filtered(lambda x: x.category_id.name in ('FTE Expense'))
                total_ot_quantity=0
                total_exp_quantity=0
                ot_category=[]
                exp_category=[]
                for rec in fte_overtime:
                    ot_category.append(rec.category_id.name)
                    total_ot_quantity+=rec.quantity
                for rec in fte_expense:
                    exp_category.append(rec.category_id.name)
                    total_exp_quantity+=rec.quantity
                ot_product=self.env['product.template'].search([('name','in',set(ot_category))])
                exp_product=self.env['product.template'].search([('name','in',set(exp_category))])
                if ot_product:
                    line_vals_debit={'product_id': ot_product.id,
                                      'name': ot_product.name,
                                      'account_id': ot_product.property_account_income_id.id,
                                      'debit': 1,
                                      'exclude_from_invoice_tab': True,
                                      'quantity': total_ot_quantity,
                                      'product_uom_id': ot_product.uom_id.id,
                                      'move_id':invoice.id
                                      }
                    move_lines.append(line_vals_debit)
                    line_vals_credit={'product_id': ot_product.id,
                                      'name': ot_product.name,
                                      'account_id': ot_product.property_account_expense_id.id,
                                      'credit': 1,
                                      'exclude_from_invoice_tab': False,
                                      'quantity': total_ot_quantity,
                                      'product_uom_id': ot_product.uom_id.id,
                                      'move_id':invoice.id
                                      }
                    move_lines.append(line_vals_credit)
                    self.env['account.move.line'].create(move_lines)
                    move_lines = []
                    if exp_product:
                        line_vals_debit={'product_id': exp_product.id,
                                          'name': exp_product.name,
                                          'account_id': exp_product.property_account_income_id.id,
                                          'debit': 1,
                                          'exclude_from_invoice_tab': True,
                                          'quantity': total_exp_quantity,
                                          'product_uom_id': exp_product.uom_id.id,
                                          'move_id':invoice.id
                                          }
                        move_lines.append(line_vals_debit)
                        line_vals_credit={'product_id': exp_product.id,
                                          'name': exp_product.name,
                                          'account_id': exp_product.property_account_expense_id.id,
                                          'credit': 1,
                                          'exclude_from_invoice_tab': False,
                                          'quantity': total_exp_quantity,
                                          'product_uom_id': exp_product.uom_id.id,
                                          'move_id':invoice.id
                                          }
                        move_lines.append(line_vals_credit)
                        self.env['account.move.line'].create(move_lines)
    #                 invoice.write({'line_ids':move_lines})
                if self._context.get('open_invoices', False):
                    return sale_orders.action_view_invoice()
                return {'type': 'ir.actions.act_window_close'}
    
            return super(SaleAdvancePaymentInv, self).create_invoices()
        elif self.invoice_policy=='Multi Invoice':
            for order_line in sale_orders.order_line:
                if self.advance_payment_method == 'delivered' and self.invoicing_timesheet_enabled:
                    if self.date_start_invoice_timesheet or self.date_end_invoice_timesheet:
                        order_line._recompute_qty_to_invoice(self.date_start_invoice_timesheet, self.date_end_invoice_timesheet)
#                     invoice=sale_orders._create_invoices(final=self.deduct_down_payments, start_date=self.date_start_invoice_timesheet, end_date=self.date_end_invoice_timesheet)
                    moves=order_line._create_invoices(final=self.deduct_down_payments, start_date=self.date_start_invoice_timesheet, end_date=self.date_end_invoice_timesheet)
                    moves._link_timesheets_to_invoice(self.date_start_invoice_timesheet, self.date_end_invoice_timesheet)
                    approvals=self.env['approval.request'].search([('task_id.sale_line_id','=',order_line.id),('request_status','=','approved'),'|',('date','>=',self.date_start_invoice_timesheet),('date','<=',self.date_end_invoice_timesheet)])
                    move_lines = []
        #             for rec in approvals:
                    sum_of_stock = 0
                    sum_of_client = 0
                    fte_overtime = approvals.filtered(lambda x: x.category_id.name in ('FTE Overtime'))
                    fte_expense = approvals.filtered(lambda x: x.category_id.name in ('FTE Expense'))
                    total_ot_quantity=0
                    total_exp_quantity=0
                    ot_category=[]
                    exp_category=[]
                    for rec in fte_overtime:
                        ot_category.append(rec.category_id.name)
                        total_ot_quantity+=rec.quantity
                    for rec in fte_expense:
                        exp_category.append(rec.category_id.name)
                        total_exp_quantity+=rec.quantity
                    ot_product=self.env['product.template'].search([('name','in',set(ot_category))])
                    exp_product=self.env['product.template'].search([('name','in',set(exp_category))])
                    if ot_product:
                        line_vals_debit={'product_id': ot_product.id,
                                          'name': ot_product.name,
                                          'account_id': ot_product.property_account_income_id.id,
                                          'debit': 1,
                                          'exclude_from_invoice_tab': True,
                                          'quantity': total_ot_quantity,
                                          'product_uom_id': ot_product.uom_id.id,
                                          'move_id':invoice.id
                                          }
                        move_lines.append(line_vals_debit)
                        line_vals_credit={'product_id': ot_product.id,
                                          'name': ot_product.name,
                                          'account_id': ot_product.property_account_expense_id.id,
                                          'credit': 1,
                                          'exclude_from_invoice_tab': False,
                                          'quantity': total_ot_quantity,
                                          'product_uom_id': ot_product.uom_id.id,
                                          'move_id':invoice.id
                                          }
                        move_lines.append(line_vals_credit)
                        self.env['account.move.line'].create(move_lines)
                        move_lines = []
                        if exp_product:
                            line_vals_debit={'product_id': exp_product.id,
                                              'name': exp_product.name,
                                              'account_id': exp_product.property_account_income_id.id,
                                              'debit': 1,
                                              'exclude_from_invoice_tab': True,
                                              'quantity': total_exp_quantity,
                                              'product_uom_id': exp_product.uom_id.id,
                                              'move_id':invoice.id
                                              }
                            move_lines.append(line_vals_debit)
                            line_vals_credit={'product_id': exp_product.id,
                                              'name': exp_product.name,
                                              'account_id': exp_product.property_account_expense_id.id,
                                              'credit': 1,
                                              'exclude_from_invoice_tab': False,
                                              'quantity': total_exp_quantity,
                                              'product_uom_id': exp_product.uom_id.id,
                                              'move_id':invoice.id
                                              }
                            move_lines.append(line_vals_credit)
                            self.env['account.move.line'].create(move_lines)
            if self._context.get('open_invoices', False):
                return sale_orders.action_view_invoice()
            return {'type': 'ir.actions.act_window_close'}
 
            return super(SaleAdvancePaymentInv, self).create_invoices()