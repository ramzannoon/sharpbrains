from openerp import models, fields, api, exceptions
from openerp.exceptions import except_orm
from openerp.exceptions import ValidationError
import pytz
from datetime import datetime, timedelta
class PlanningSlot(models.Model):
    _inherit='planning.slot'
    task_id=fields.Many2one('project.task','Service Order')
    
    def _get_tz(self):
        
        return (self.task_id.tz
                or self.env.user.tz
                or self.employee_id.tz
                or self._context.get('tz')
                or self.company_id.resource_calendar_id.tz
                or 'UTC')
#     def write(self,vals):
#         obj=super(PlanningSlot, self).write(vals)
#         old_tz = pytz.timezone('UTC')
#         new_tz = pytz.timezone(self.task_id.tz)
#         dt = self.start_datetime.utcnow()
#         
#         dt = datetime.strptime(str(self.start_datetime),"%Y-%m-%d %H:%M:%S")
# #         dt = new_tz.localize(dt)
#         dt = old_tz.localize(dt).astimezone(new_tz)
# #         dt = dt.astimezone(new_tz)
# #         dt = dt.strftime("%Y-%m-%d %H:%M:%S")
# 
# #     return dt
#         print (dt)
#         task_tz=self.task_id.
        
