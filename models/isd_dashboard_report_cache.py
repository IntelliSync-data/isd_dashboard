from odoo import fields, models


class IsdDashboardReportCache(models.Model):
    _name = 'isd.dashboard.report.cache'
    _description = 'Dashboard Report Cache'
    _order = 'create_date desc'

    report_key = fields.Char(string='Report Key', required=True, index=True)
    label = fields.Char(string='Label')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    result_html = fields.Text(string='Result HTML')
    prompt_used = fields.Text(string='Prompt Used')
