# -*- coding: utf-8 -*-

from odoo import fields, models, api


class IsdDashboardUsage(models.Model):
    _name = 'isd.dashboard.usage'
    _description = 'Dashboard Daily Usage'
    _order = 'usage_date desc'
    _rec_name = 'usage_date'

    usage_date = fields.Date(string='Date', required=True, index=True)
    count = fields.Integer(string='Prompt Count', default=0)

    _sql_constraints = [
        ('unique_date', 'UNIQUE(usage_date)', 'Only one usage record per date.'),
    ]

    @api.model
    def increment(self):
        """Increment today's usage count. Called after each successful prompt."""
        today = fields.Date.today()
        existing = self.sudo().search([('usage_date', '=', today)], limit=1)
        if existing:
            existing.sudo().write({'count': existing.count + 1})
        else:
            self.sudo().create({'usage_date': today, 'count': 1})
