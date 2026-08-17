# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class ResConfigSettings(models.TransientModel):
    """Extension of res.config.settings for Albirru theme configuration.

    Exposes company-level branding fields in the General Settings
    interface for easy configuration of backend logos, favicon,
    tab name, login page appearance, and menu backgrounds.
    """
    _inherit = 'res.config.settings'

    # Whether users may personalise the theme. Stored on albirru.theme.config
    # rather than res.company, so it cannot be a related field.
    albirru_theme_scope = fields.Selection(
        selection=[
            ('user', 'Each user can personalize'),
            ('company', 'Company-wide (locked)'),
        ],
        string='Theme Personalization',
        compute='_compute_albirru_theme_scope',
        inverse='_inverse_albirru_theme_scope',
        readonly=False,
        help='Company-wide applies one look to everyone and hides the '
             'personalization controls. Users keep their own dark mode '
             'preference either way. Settings each user already personalized '
             'are kept and come back if you switch to per-user again.'
    )

    @api.depends('company_id')
    def _compute_albirru_theme_scope(self):
        # sudo(): a settings form may be opened before the configuration record
        # exists, and reading it must not depend on the theme model's ACL.
        Config = self.env['albirru.theme.config'].sudo()
        for record in self:
            config = Config.search(
                [('company_id', '=', record.company_id.id)], limit=1
            )
            record.albirru_theme_scope = config.theme_scope or 'user'

    def _inverse_albirru_theme_scope(self):
        # res.config.settings is already restricted to administrators, but this
        # writes a setting that governs every user of the company, so the check
        # is repeated rather than assumed.
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only administrators can change the theme scope.'))
        for record in self:
            config = self.env['albirru.theme.config'].with_company(
                record.company_id
            ).get_current_config()
            config.sudo().theme_scope = record.albirru_theme_scope

    # Branding (stored in res.company)
    albirru_backend_logo = fields.Binary(
        related='company_id.albirru_backend_logo',
        readonly=False,
        string='Backend Logo'
    )
    albirru_backend_logo_icon = fields.Binary(
        related='company_id.albirru_backend_logo_icon',
        readonly=False,
        string='Backend Logo Icon'
    )
    albirru_favicon = fields.Binary(
        related='company_id.albirru_favicon',
        readonly=False,
        string='Favicon'
    )
    albirru_tab_name = fields.Char(
        related='company_id.albirru_tab_name',
        readonly=False,
        string='Browser Tab Name'
    )

    # Login Page Branding
    albirru_login_background = fields.Binary(
        related='company_id.albirru_login_background',
        readonly=False,
        string='Login Background'
    )
    albirru_login_background_color = fields.Char(
        related='company_id.albirru_login_background_color',
        readonly=False,
        string='Login Background Color'
    )
    albirru_login_style = fields.Selection(
        related='company_id.albirru_login_style',
        readonly=False,
        string='Login Layout Style',
        required=True
    )



