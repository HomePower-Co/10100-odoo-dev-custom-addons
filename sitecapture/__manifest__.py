{
    'name': 'Site Capture Extension',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'Add custom fields to CRM Lead',
    'description': """
        This module adds custom fields to the CRM Lead model.
    """,
    'author': 'Juan Diego Escobar',
    'depends': ['crm'],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
}