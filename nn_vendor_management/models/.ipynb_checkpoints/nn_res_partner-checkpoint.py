# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class NNResPartner(models.Model):
    _name = 'nn.res.partner'
    _description = 'Vendor Management'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', efault=lambda self: self.env.user)
    vendor_company = fields.Char(string='Vendor Company', required=True)
    poc = fields.Char(string='Point Of Contract' , required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    region = fields.Char(string='Region')
    country_id = fields.Many2one('res.country', string='Country')
    city_id = fields.Char(string='City')
    rate = fields.Char(string='Rate', required=True)
    remarks = fields.Char(string='Remarks')
    
    
    