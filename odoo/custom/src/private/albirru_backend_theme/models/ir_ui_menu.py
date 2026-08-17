# -*- coding: utf-8 -*-
# Albirru Backend Theme - Menu Extension
# Compatible with Odoo 19

from odoo import models, fields


class IrUiMenu(models.Model):
    """Extension of ir.ui.menu for Albirru theme customization.
    
    Adds fields to support custom app grouping and icon customization
    in the Albirru theme's App Drawer and sidebar navigation.
    """
    _inherit = 'ir.ui.menu'

    albirru_app_group_id = fields.Many2one(
        'albirru.app.group',
        string='App Group',
        ondelete='set null',
        help='Group this application belongs to in the App Drawer'
    )
    icon_img = fields.Image(
        string='Custom Icon Image',
        help='Custom icon image for this menu'
    )
    use_icon = fields.Boolean(
        string='Use Custom Icon Class',
        default=False,
        help='Enable to use a custom icon class instead of default icon'
    )
    icon_class_name = fields.Char(
        string='Icon Class Name',
        help='FontAwesome or other icon class (e.g., fa-home, fa-cog)'
    )
