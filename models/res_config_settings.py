import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

from odoo.addons.isd_dashboard.controllers.dashboard import _DEFAULT_SYSTEM_PROMPT


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    isd_dashboard_api_key = fields.Char(
        string='Anthropic API Key',
        help='API key từ console.anthropic.com (sk-ant-api03-...)',
    )
    isd_dashboard_claude_model = fields.Selection(
        string='Claude Model',
        selection=[
            ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5 — Nhanh, rẻ nhất'),
            ('claude-sonnet-4-6', 'Claude Sonnet 4.6 — Cân bằng (khuyến nghị)'),
            ('claude-opus-4-6', 'Claude Opus 4.6 — Mạnh nhất, chậm hơn'),
        ],
        default='claude-sonnet-4-6',
    )
    isd_dashboard_mcp_token_id = fields.Many2one(
        'isd.mcp.config',
        string='MCP Config (PhotoApp)',
    )
    isd_dashboard_mcp_server_name = fields.Char(
        string='Tên MCP Server',
        default='KClickPhotoApp',
    )
    isd_dashboard_system_prompt = fields.Text(
        string='System Prompt',
    )

    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        token_id = ICP.get_param('isd_dashboard.mcp_token_id', '')
        res.update(
            isd_dashboard_api_key=ICP.get_param('isd_dashboard.api_key', ''),
            isd_dashboard_claude_model=ICP.get_param('isd_dashboard.claude_model', 'claude-sonnet-4-6'),
            isd_dashboard_mcp_token_id=int(token_id) if token_id and token_id.isdigit() else False,
            isd_dashboard_mcp_server_name=ICP.get_param('isd_dashboard.mcp_server_name', 'KClickPhotoApp'),
            isd_dashboard_system_prompt=ICP.get_param('isd_dashboard.system_prompt', _DEFAULT_SYSTEM_PROMPT),
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('isd_dashboard.api_key', self.isd_dashboard_api_key or '')
        ICP.set_param('isd_dashboard.claude_model', self.isd_dashboard_claude_model or 'claude-sonnet-4-6')
        ICP.set_param('isd_dashboard.mcp_token_id', str(self.isd_dashboard_mcp_token_id.id) if self.isd_dashboard_mcp_token_id else '')
        ICP.set_param('isd_dashboard.mcp_server_name', self.isd_dashboard_mcp_server_name or 'KClickPhotoApp')
        ICP.set_param('isd_dashboard.system_prompt', self.isd_dashboard_system_prompt or _DEFAULT_SYSTEM_PROMPT)
