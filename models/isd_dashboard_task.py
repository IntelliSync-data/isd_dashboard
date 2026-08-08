from odoo import fields, models


class IsdDashboardTask(models.Model):
    _name = 'isd.dashboard.task'
    _description = 'AI Dashboard Task'
    _order = 'create_date desc'

    task_id = fields.Char(string='Task ID', required=True, index=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='pending', required=True)
    result_html = fields.Text(string='Result HTML')
    error_message = fields.Text(string='Error Message')
