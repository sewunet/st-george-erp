# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def color_scheme(self):
        """Select the dark asset bundle for users who enabled dark mode.

        Odoo picks the stylesheet bundle from this value at render time
        (web.assets_web_dark vs web.assets_web), which means the very first
        paint is already correct - no flash of light content - and light-mode
        users never download the dark stylesheet at all.
        """
        try:
            user = self.env.user
            if user and not user._is_public() and user.albirru_dark_mode:
                return 'dark'
        except Exception as e:
            _logger.warning('Failed to resolve Albirru color scheme: %s', e)
        return super().color_scheme()

    def session_info(self):
        """Extend session info with Albirru theme data"""
        result = super().session_info()

        try:
            if request and request.session.uid and self.env.user.has_group('base.group_user'):
                user = self.env.user
                company = self.env.company

                # Get theme settings from albirru.theme.config
                try:
                    theme_settings = user.get_albirru_theme_settings()
                except Exception as e:
                    _logger.warning('Failed to get theme settings: %s', e)
                    theme_settings = self._get_default_theme_settings()

                # Get bookmarks
                try:
                    bookmarks = user.albirru_bookmark_ids.get_bookmarks_data() if user.albirru_bookmark_ids else []
                except Exception as e:
                    _logger.warning('Failed to get bookmarks: %s', e)
                    bookmarks = []

                # Get branding info from company
                try:
                    branding = {
                        'company_id': company.id,
                        'tab_name': getattr(company, 'albirru_tab_name', None) or 'Odoo',
                        'has_logo': bool(getattr(company, 'albirru_backend_logo', False)),
                        'has_logo_icon': bool(getattr(company, 'albirru_backend_logo_icon', False)),
                        'has_favicon': bool(getattr(company, 'albirru_favicon', False)),
                    }
                except Exception as e:
                    _logger.warning('Failed to get branding: %s', e)
                    branding = {
                        'tab_name': 'Odoo',
                        'has_logo': False,
                        'has_logo_icon': False,
                        'has_favicon': False,
                    }

                try:
                    overridden = user.get_albirru_overridden_keys()
                except Exception as e:
                    _logger.warning('Failed to get theme overrides: %s', e)
                    overridden = []

                result.update({
                    'albirru_theme_installed': True,
                    'albirru_theme_settings': theme_settings,
                    'albirru_theme_overridden': overridden,
                    'albirru_bookmarks': bookmarks,
                    'albirru_branding': branding,
                    'albirru_is_admin': user.has_group('base.group_system'),
                    # Drives the Quick Settings panel: locked hides every
                    # personal control except dark mode.
                    'albirru_theme_locked': theme_settings.get('theme_scope') == 'company',
                })
        except Exception as e:
            _logger.error('Failed to add Albirru theme session info: %s', e)
            result['albirru_theme_installed'] = True
            result['albirru_theme_settings'] = self._get_default_theme_settings()
            result['albirru_theme_overridden'] = []
            result['albirru_bookmarks'] = []
            result['albirru_branding'] = {
                'tab_name': 'Odoo',
                'has_logo': False,
                'has_logo_icon': False,
                'has_favicon': False
            }
            result['albirru_is_admin'] = False
            result['albirru_theme_locked'] = False

        return result

    def _get_default_theme_settings(self):
        """Return default theme settings"""
        return {
            'theme_scope': 'user',
            'theme_style': 'rounded',
            'color_scheme': 'scheme_1',
            'dark_mode': False,
            'sidebar_pinned': True,
            'sidebar_position': 'left',
            'open_drawer_on_home': True,
            'font_family': 'inter',
            'font_size': 'medium',
            'chatter_position': 'right',
            'list_row_height': 'comfortable',
            'list_sticky_header': True,
            'use_custom_colors': False,
            'primary_color': '#714B67',
            'secondary_color': '#ffffff',
            'accent_color': '#017e84',
            'button_style': 'filled',
            'input_style': 'bordered',
            'loader_style': 'spinner',
        }
