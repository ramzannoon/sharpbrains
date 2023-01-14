# -*- coding: utf-8 -*-
{
    'name': "Vendor Management",

    'summary': """
        Vendor Management
        """,

    'description': """
        Vendor Management
    """,

    'author': "Sharpbrains",
    'website': "http://www.sharpbrains.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'views/nn_res_partner_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
