# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.models import Constraint

# Settings a user may override for themselves. Everything the company config
# exposes is personal taste except the shared menu background, which is a
# company asset rather than a preference.
USER_OVERRIDABLE_FIELDS = (
    'theme_style',
    'color_scheme',
    'use_custom_colors',
    'primary_color',
    'secondary_color',
    'accent_color',
    'sidebar_position',
    'chatter_position',
    'list_row_height',
    'list_sticky_header',
    'font_family',
    'font_size',
    'button_style',
    'input_style',
    'loader_style',
    'open_drawer_on_home',
)

# Settings only an administrator can change, for the whole company.
COMPANY_ONLY_FIELDS = (
    'menu_background',
    'menu_bg_opacity',
    'theme_scope',
)


class AlbirruThemeConfig(models.Model):
    _name = 'albirru.theme.config'
    _description = 'Albirru Theme Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', default='Default')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        ondelete='cascade'
    )

    # Who owns the look of the backend.
    #
    # 'user'    - the company values below are defaults; every user may
    #             personalise them for themselves (the historic behaviour).
    # 'company' - the company values are the only ones that apply. Personal
    #             overrides already stored are kept but ignored, so switching
    #             back to 'user' restores everyone's own choices instead of
    #             silently discarding them.
    #
    # Dark mode and the pinned sidebar are deliberately outside this switch:
    # they are accessibility and workspace concerns, not branding.
    theme_scope = fields.Selection([
        ('user', 'Each user can personalize'),
        ('company', 'Company-wide (locked)'),
    ], default='user', required=True, string='Theme Personalization')

    # Theme Style
    theme_style = fields.Selection([
        ('rounded', 'Rounded'),
        ('standard', 'Standard'),
        ('square', 'Square'),
    ], default='rounded', string='Theme Style')

    # Color Scheme
    color_scheme = fields.Selection([
        ('scheme_1', 'Odoo Purple'),
        ('scheme_2', 'Green Nature'),
        ('scheme_3', 'Purple Elegant'),
        ('scheme_4', 'Orange Warm'),
        ('scheme_5', 'Red Bold'),
        ('scheme_6', 'Teal Fresh'),
        ('scheme_7', 'Pink Rose'),
        ('scheme_8', 'Blue Ocean'),
        ('scheme_9', 'Indigo Deep'),
        ('scheme_10', 'Amber Gold'),
        ('scheme_11', 'Cyan Sky'),
        ('scheme_12', 'Brown Earth'),
        ('scheme_13', 'Black Elegance'),
        ('scheme_14', 'Lime Fresh'),
        ('scheme_15', 'Deep Purple'),
        ('scheme_16', 'Light Blue'),
        ('scheme_17', 'Grey Steel'),
        ('scheme_18', 'Blue Grey'),
    ], default='scheme_1', string='Color Scheme')

    # Custom Colors
    use_custom_colors = fields.Boolean(string='Use Custom Colors')
    primary_color = fields.Char(string='Primary Color', default='#714B67')
    secondary_color = fields.Char(string='Secondary Color', default='#ffffff')
    accent_color = fields.Char(string='Accent Color', default='#017e84')

    # NOTE: dark mode and the sidebar pinned state are user preferences, not
    # company settings. They live on res.users (albirru_dark_mode /
    # albirru_sidebar_pinned) and are read from there by
    # res.users.get_albirru_theme_settings().

    # Sidebar Settings
    sidebar_position = fields.Selection([
        ('left', 'Left Sidebar'),
        ('top', 'Top Horizontal'),
    ], default='left', string='Menu Position')

    open_drawer_on_home = fields.Boolean(
        string='Open App Drawer on Home',
        default=True,
        help='Show the App Drawer when opening Odoo without a specific action. '
             'Disable to keep the standard Odoo behaviour of loading the first '
             'available application.'
    )



    # Form View Settings
    chatter_position = fields.Selection([
        ('right', 'Right Side'),
        ('bottom', 'Bottom'),
    ], default='right', string='Chatter Position')

    # List View Settings
    list_row_height = fields.Selection([
        ('compact', 'Compact'),
        ('comfortable', 'Comfortable'),
    ], default='comfortable', string='List Row Height')

    list_sticky_header = fields.Boolean(string='Sticky List Header', default=True)

    # Font Settings
    font_family = fields.Selection([
        ('inter', 'Inter'),
        ('roboto', 'Roboto'),
        ('poppins', 'Poppins'),
        ('open_sans', 'Open Sans'),
        ('lato', 'Lato'),
        ('nunito', 'Nunito Sans'),
    ], default='inter', string='Font Family')

    font_size = fields.Selection([
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ], default='medium', string='Font Size')

    # UI Elements
    button_style = fields.Selection([
        ('filled', 'Filled'),
        ('outlined', 'Outlined'),
        ('soft', 'Soft'),
    ], default='filled', string='Button Style')

    input_style = fields.Selection([
        ('bordered', 'Bordered'),
        ('underlined', 'Underlined'),
        ('filled', 'Filled'),
    ], default='bordered', string='Input Style')

    # Loader
    loader_style = fields.Selection([
        ('spinner', 'Spinner'),
        ('dots', 'Dots'),
        ('bar', 'Progress Bar'),
    ], default='spinner', string='Loader Style')

    # Menu Background Image (for sidebar and app drawer)
    menu_background = fields.Binary(
        string='Menu Background Image',
        help='Background image for sidebar and app drawer'
    )
    menu_bg_opacity = fields.Integer(
        string='Background Opacity (%)',
        default=15,
        help='Opacity of the background image (0-100). Lower value = more transparent.'
    )

    # Odoo 19 constraint syntax
    _constraints = [
        Constraint(
            'unique(company_id)',
            'Only one theme configuration per company is allowed!',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to prevent duplicate configs per company"""
        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            existing = self.sudo().search([('company_id', '=', company_id)], limit=1)
            if existing:
                raise UserError(_(
                    'A theme configuration already exists for this company. '
                    'Only one configuration per company is allowed.'
                ))
        return super().create(vals_list)

    def unlink(self):
        """Prevent deletion of theme configs through normal UI"""
        for record in self:
            # Allow deletion only in certain contexts (like during module uninstall)
            if not self.env.context.get('force_unlink'):
                raise UserError(_(
                    'Theme configuration cannot be deleted. '
                    'It is required for the theme to work properly.'
                ))
        return super().unlink()

    @api.model
    def get_current_config(self):
        """Get or create config for current company.

        Only call this from an authenticated context: it writes to the database
        when no configuration exists yet. Use :meth:`get_display_config` for
        read-only rendering (public pages, reports).
        """
        company = self.env.company
        config = self.get_display_config()
        if not config:
            # Create default config for company
            config = self.sudo().create({
                'name': f'{company.name} Theme',
                'company_id': company.id,
            })
        return config

    @api.model
    def get_display_config(self):
        """Return the config of the current company without ever creating one.

        Returns an empty recordset when the company has no configuration yet;
        field access on it yields falsy values, so callers can rely on their own
        defaults. This keeps public requests (e.g. the login page) free of any
        database write side effect.
        """
        return self.sudo().search(
            [('company_id', '=', self.env.company.id)], limit=1
        )

    def get_theme_values(self):
        """Return theme configuration as dictionary for frontend"""
        self.ensure_one()
        return {
            # Not a visual setting: the web client reads it to know whether the
            # personalisation controls should be offered at all.
            'theme_scope': self.theme_scope or 'user',
            'theme_style': self.theme_style,
            'color_scheme': self.color_scheme,
            'use_custom_colors': self.use_custom_colors,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'sidebar_position': self.sidebar_position,
            'open_drawer_on_home': self.open_drawer_on_home,

            'chatter_position': self.chatter_position,
            'list_row_height': self.list_row_height,
            'list_sticky_header': self.list_sticky_header,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'button_style': self.button_style,
            'input_style': self.input_style,
            'loader_style': self.loader_style,
            'has_menu_background': bool(self.menu_background),
            'menu_bg_opacity': self.menu_bg_opacity or 15,
            'menu_bg_cache_key': int(self.write_date.timestamp()) if self.write_date else 0,
        }

    def save_setting(self, field, value):
        """Save a single setting value.

        The write is intentionally not sudo'ed: callers must hold write access
        on the configuration. Membership is checked against _fields rather than
        hasattr(), which would also accept method names such as 'unlink'.

        Returns:
            bool: True when the field exists and was written
        """
        self.ensure_one()
        if field not in self._fields:
            return False
        self.write({field: value})
        return True

    def action_apply_refresh(self):
        """Save settings and reload page to apply changes"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
