# -*- coding: utf-8 -*-

from odoo import fields, models, api


class IsdDashboardPlan(models.Model):
    _name = 'isd.dashboard.plan'
    _description = 'Dashboard Usage Plan'
    _order = 'date_from desc'

    name = fields.Char(string='Plan Name', required=True)
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    prompt_limit = fields.Integer(
        string='Prompt Limit',
        help='Maximum prompts allowed in this plan period. 0 = unlimited.',
        default=0,
    )
    report_limit = fields.Integer(
        string='Report Limit',
        help='Maximum saved reports allowed. 0 = unlimited.',
        default=0,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Note')

    # Computed
    prompt_used = fields.Integer(string='Prompts Used', compute='_compute_usage')
    report_count = fields.Integer(string='Reports Saved', compute='_compute_report_count')

    @api.depends('date_from', 'date_to')
    def _compute_usage(self):
        Usage = self.env['isd.dashboard.usage']
        for plan in self:
            if plan.date_from and plan.date_to:
                plan.prompt_used = sum(Usage.search([
                    ('usage_date', '>=', plan.date_from),
                    ('usage_date', '<=', plan.date_to),
                ]).mapped('count'))
            else:
                plan.prompt_used = 0

    @api.depends('date_from', 'date_to')
    def _compute_report_count(self):
        Report = self.env['isd.dashboard.report']
        for plan in self:
            if plan.date_from and plan.date_to:
                plan.report_count = Report.search_count([
                    ('state', '=', 'done'),
                    ('create_date', '>=', plan.date_from),
                    ('create_date', '<=', plan.date_to),
                ])
            else:
                plan.report_count = 0

    @api.model
    def get_active_plan(self):
        """Get the plan that covers today."""
        today = fields.Date.today()
        return self.search([
            ('active', '=', True),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ], limit=1, order='date_from desc')
