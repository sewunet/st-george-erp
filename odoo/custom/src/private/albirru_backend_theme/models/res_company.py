# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Extension of res.company for Albirru theme branding.
    
    Adds fields to customize backend branding including logo,
    favicon, tab name, login page appearance, and menu backgrounds per company.
    """
    _inherit = 'res.company'

    # Backend Branding (kept in company for General Settings)
    albirru_backend_logo = fields.Binary(string='Backend Logo')
    albirru_backend_logo_icon = fields.Binary(string='Backend Logo Icon (Small)')
    albirru_favicon = fields.Binary(string='Favicon')
    albirru_tab_name = fields.Char(string='Browser Tab Name', default='Odoo')

    # Login Page Branding
    albirru_login_background = fields.Binary(string='Login Background Image')
    albirru_login_background_color = fields.Char(string='Login Background Color', default='#f0f4f7')
    albirru_login_style = fields.Selection([
        ('glass', 'Centered Glass (Default)'),
        ('split', 'Split Screen Professional'),
        ('minimal', 'Immersive Minimalist')
    ], string='Login Layout Style', default='glass')



