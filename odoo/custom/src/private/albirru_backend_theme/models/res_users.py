# -*- coding: utf-8 -*-
from odoo import fields, models, api

from .theme_config import USER_OVERRIDABLE_FIELDS


class ResUsers(models.Model):
    """Extension of res.users for user-specific Albirru theme preferences.
    
    User-level settings override company-level settings for:
    - Dark/Light mode
    - Sidebar pinned state
    - Bookmarks (always user-specific)
    """
    _inherit = 'res.users'

    # User-specific theme preferences
    albirru_dark_mode = fields.Boolean(
        string='Dark Mode',
        default=False,
        help='Enable dark mode for this user'
    )
    albirru_sidebar_pinned = fields.Boolean(
        string='Sidebar Pinned',
        default=True,
        help='Keep sidebar pinned/expanded for this user'
    )

    albirru_theme_overrides = fields.Json(
        string='Theme Overrides',
        default=dict,
        help='Per-user overrides on top of the company theme configuration. '
             'A key that is absent means "follow the company default".'
    )


    # User Bookmarks
    albirru_bookmark_ids = fields.One2many(
        'albirru.bookmark',
        'user_id',
        string='Bookmarks'
    )

    # Allow users to update their own theme preferences
    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'albirru_dark_mode',
            'albirru_sidebar_pinned',
            'albirru_theme_overrides',
        ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'albirru_dark_mode',
            'albirru_sidebar_pinned',
            'albirru_theme_overrides',
        ]

    def get_albirru_theme_settings(self):
        """Get the effective theme settings for this user.

        Resolution order, lowest priority first:
          1. the company configuration (albirru.theme.config)
          2. this user's own overrides, unless the company locked the theme
          3. dark_mode / sidebar_pinned, which are user-owned outright

        Returns:
            dict: the values the web client should apply
        """
        self.ensure_one()
        config = self.env['albirru.theme.config'].get_current_config()
        settings = config.get_theme_values()

        # Apply this user's personal overrides on top of the company defaults.
        # A locked company skips this layer without erasing it, so unlocking
        # gives every user their own choices back.
        if config.theme_scope != 'company':
            for key, value in (self.albirru_theme_overrides or {}).items():
                if key in USER_OVERRIDABLE_FIELDS:
                    settings[key] = value

        # These two have always belonged to the user alone.
        settings['dark_mode'] = self.albirru_dark_mode
        settings['sidebar_pinned'] = self.albirru_sidebar_pinned

        return settings

    def get_albirru_overridden_keys(self):
        """Return the settings this user has personalised.

        The web client uses it to show which controls differ from the company
        default and to offer a reset. While the company theme is locked nothing
        differs, so the stored overrides are reported as absent.
        """
        self.ensure_one()
        if self.env['albirru.theme.config'].get_current_config().theme_scope == 'company':
            return []
        return sorted(
            key for key in (self.albirru_theme_overrides or {})
            if key in USER_OVERRIDABLE_FIELDS
        )

    def save_albirru_user_setting(self, field, value):
        """Save a user-owned boolean preference.

        Args:
            field: 'dark_mode' or 'sidebar_pinned'
            value: Boolean value

        Returns:
            bool: True if saved successfully
        """
        self.ensure_one()
        field_map = {
            'dark_mode': 'albirru_dark_mode',
            'sidebar_pinned': 'albirru_sidebar_pinned',
        }
        if field in field_map:
            self.sudo().write({field_map[field]: value})
            return True
        return False

    def is_albirru_theme_locked(self):
        """Whether the company forbids personal theme settings.

        Dark mode and the pinned sidebar stay available either way; they are
        stored on res.users and never travel through the override layer.
        """
        self.ensure_one()
        config = self.env['albirru.theme.config'].get_current_config()
        return config.theme_scope == 'company'

    def set_albirru_theme_override(self, field, value):
        """Override one theme setting for this user only.

        Args:
            field: one of USER_OVERRIDABLE_FIELDS
            value: already validated by the caller

        Returns:
            bool: True if stored
        """
        self.ensure_one()
        if field not in USER_OVERRIDABLE_FIELDS:
            return False
        # Enforced here rather than only in the controller, so an override
        # cannot be planted through the ORM either.
        if self.is_albirru_theme_locked():
            return False
        # Json fields are replaced wholesale; mutating in place would not be
        # detected as a change by the ORM.
        overrides = dict(self.albirru_theme_overrides or {})
        overrides[field] = value
        self.sudo().write({'albirru_theme_overrides': overrides})
        return True

    def clear_albirru_theme_override(self, field=None):
        """Drop one override, or all of them, falling back to company defaults.

        Args:
            field: the setting to reset, or None to reset everything

        Returns:
            bool: True if anything changed
        """
        self.ensure_one()
        overrides = dict(self.albirru_theme_overrides or {})

        if field is None:
            if not overrides:
                return False
            self.sudo().write({'albirru_theme_overrides': {}})
            return True

        if field not in overrides:
            return False
        del overrides[field]
        self.sudo().write({'albirru_theme_overrides': overrides})
        return True


class AlbirruBookmark(models.Model):
    """User bookmarks for quick navigation.
    
    Bookmarks are user-specific and stored per user. Each bookmark
    contains a name, URL, and optional icon class.
    """
    _name = 'albirru.bookmark'
    _description = 'User Bookmarks'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL', required=True)
    icon = fields.Char(string='Icon', default='fa-bookmark')
    sequence = fields.Integer(string='Sequence', default=10)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')

    def get_bookmarks_data(self):
        """Return bookmarks as list of dicts for frontend.
        
        Returns:
            list: List of bookmark dictionaries with id, name, url, and icon.
        """
        return [{
            'id': bookmark.id,
            'name': bookmark.name,
            'url': bookmark.url,
            'icon': bookmark.icon,
        } for bookmark in self]

