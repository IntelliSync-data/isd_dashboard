from odoo import fields, models


class IsdDashboardReport(models.Model):
    _name = 'isd.dashboard.report'
    _description = 'Dashboard Report'
    _order = 'create_date desc'

    report_type = fields.Selection([
        ('revenue', 'Revenue Report'),
        ('comparison', 'Revenue Comparison'),
    ], string='Report Type', required=True, index=True)

    period_type = fields.Selection([
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Period Type', required=True)

    period_start = fields.Date(string='Period Start', required=True, index=True)
    period_end = fields.Date(string='Period End', required=True)
    period_label = fields.Char(string='Period Label')

    compare_period_start = fields.Date(string='Compare Period Start')
    compare_period_end = fields.Date(string='Compare Period End')
    compare_period_label = fields.Char(string='Compare Period Label')

    result_html = fields.Text(string='Result HTML')
    prompt_used = fields.Text(string='Prompt')
    state = fields.Selection([
        ('generating', 'Generating'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='Status', default='done', required=True)
    error_message = fields.Text(string='Error Message')
