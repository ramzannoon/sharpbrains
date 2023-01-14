# -*- coding: utf-8 -*-
# from odoo import http


# class NnVendorManagement(http.Controller):
#     @http.route('/nn_vendor_management/nn_vendor_management/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nn_vendor_management/nn_vendor_management/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('nn_vendor_management.listing', {
#             'root': '/nn_vendor_management/nn_vendor_management',
#             'objects': http.request.env['nn_vendor_management.nn_vendor_management'].search([]),
#         })

#     @http.route('/nn_vendor_management/nn_vendor_management/objects/<model("nn_vendor_management.nn_vendor_management"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nn_vendor_management.object', {
#             'object': obj
#         })
