{
    'name': 'ISD AI Dashboard',
    'version': '18.0.1.0.0',
    'category': 'ISD Modules',
    'summary': 'AI-powered dashboard using Claude + PhotoApp MCP',
    'depends': ['base', 'web', 'board', 'isd_mcp_photoapp'],
    'data': [
        'security/isd_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/isd_dashboard_config_views.xml',
        'views/isd_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'isd_dashboard/static/src/js/dashboard_component.js',
            'isd_dashboard/static/src/xml/dashboard_component.xml',
        ],
    },
    'external_dependencies': {'python': ['anthropic']},
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
