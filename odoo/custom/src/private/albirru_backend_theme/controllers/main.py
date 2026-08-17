# -*- coding: utf-8 -*-
import base64
import binascii
import logging
import re
from urllib.parse import urlparse
from odoo import http
from odoo.http import request

from ..models.theme_config import USER_OVERRIDABLE_FIELDS, COMPANY_ONLY_FIELDS

_logger = logging.getLogger(__name__)

# Validation rules for every settable theme field, shared by the save and
# reset endpoints. Keys not listed here cannot be written at all.
FIELD_VALIDATORS = {
    # Selection fields
    'theme_style': {'type': str, 'values': ['rounded', 'standard', 'square']},
    'color_scheme': {'type': str, 'values': [f'scheme_{i}' for i in range(1, 19)]},
    'sidebar_position': {'type': str, 'values': ['left', 'top']},
    'chatter_position': {'type': str, 'values': ['right', 'bottom']},
    'font_family': {'type': str, 'values': ['inter', 'roboto', 'poppins', 'open_sans', 'lato', 'nunito']},
    'font_size': {'type': str, 'values': ['small', 'medium', 'large']},
    'list_row_height': {'type': str, 'values': ['compact', 'comfortable']},
    'button_style': {'type': str, 'values': ['filled', 'outlined', 'soft']},
    'input_style': {'type': str, 'values': ['bordered', 'underlined', 'filled']},
    'loader_style': {'type': str, 'values': ['spinner', 'dots', 'bar']},
    # Boolean fields
    'use_custom_colors': {'type': bool},
    'list_sticky_header': {'type': bool},
    'open_drawer_on_home': {'type': bool},
    # Color fields (hex format)
    'primary_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
    'secondary_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
    'accent_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
    # Integer fields
    'menu_bg_opacity': {'type': int, 'min': 0, 'max': 100},
    # Binary fields
    'menu_background': {'type': 'binary'},
}

# Settings that belong to the user outright, stored as columns on res.users.
USER_OWNED_FIELDS = ('dark_mode', 'sidebar_pinned')

# Maximum decoded size accepted for an uploaded menu background image.
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB

# Magic byte signatures of the image formats we are willing to store and serve.
IMAGE_SIGNATURES = (
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
)


def _detect_image_type(data):
    """Return the mimetype of ``data`` if it is a supported image, else None.

    Args:
        data: raw (already decoded) image bytes

    Returns:
        str|None: mimetype, or None when the payload is not a supported image
    """
    for signature, mimetype in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return mimetype
    # WEBP: 'RIFF' <4 byte size> 'WEBP'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


class AlbirruThemeController(http.Controller):
    """Controller for Albirru Backend Theme API endpoints"""

    def _is_safe_url(self, url):
        """Validate URL to prevent XSS attacks
        
        Only allows:
        - http:// and https:// URLs
        - Relative URLs starting with /
        - Hash URLs starting with #
        
        Blocks:
        - javascript: URLs
        - data: URLs
        - vbscript: URLs
        - Other potentially dangerous schemes
        
        Args:
            url: URL string to validate
            
        Returns:
            bool: True if URL is safe, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check for dangerous schemes (case-insensitive)
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
        url_lower = url.lower()
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return False
        
        # Allow relative URLs
        if url.startswith('/') or url.startswith('#'):
            return True
        
        # Parse and validate absolute URLs
        try:
            parsed = urlparse(url)
            # Only allow http and https schemes
            return parsed.scheme in ('http', 'https', '')
        except Exception:
            return False


    def _validate_image_upload(self, b64_value):
        """Validate a base64 image payload before it is stored.

        Guards against oversized uploads and against storing arbitrary
        (non-image) data in a field that is later served back to browsers.

        Args:
            b64_value: base64-encoded payload as received from the client

        Returns:
            str|None: an error message, or None when the payload is acceptable
        """
        # A base64 string is ~4/3 the size of its decoded payload; reject
        # oversized input before spending memory on decoding it.
        if len(b64_value) > (MAX_IMAGE_SIZE // 3) * 4 + 4:
            return 'Image is too large (maximum 2 MB).'

        try:
            data = base64.b64decode(b64_value, validate=True)
        except (binascii.Error, ValueError):
            return 'Invalid image data.'

        if len(data) > MAX_IMAGE_SIZE:
            return 'Image is too large (maximum 2 MB).'

        if not _detect_image_type(data):
            return 'Unsupported image format. Use PNG, JPEG, GIF or WEBP.'

        return None

    @http.route('/albirru_backend_theme/favicon', type='http', auth='public')
    def get_favicon(self, **kwargs):
        """Serve custom favicon from company settings"""
        company = request.env.company

        if company.albirru_favicon:
            favicon_data = base64.b64decode(company.albirru_favicon)
            return request.make_response(
                favicon_data,
                headers=[
                    ('Content-Type', 'image/x-icon'),
                    ('Cache-Control', 'public, max-age=86400'),
                ]
            )

        # Fallback to default Odoo favicon
        return request.redirect('/web/static/img/favicon.ico')

    @http.route('/albirru_backend_theme/menu_background', type='http', auth='user')
    def get_menu_background(self, **kwargs):
        """Serve menu background image from theme config (unified for sidebar and app drawer)"""
        config = request.env['albirru.theme.config'].get_current_config()
        
        if config.menu_background:
            img_data = base64.b64decode(config.menu_background)
            content_type = _detect_image_type(img_data)
            if not content_type:
                # Stored payload is not a recognised image - refuse to serve it
                # rather than letting the browser sniff its type.
                return request.make_response('', status=404)

            return request.make_response(
                img_data,
                headers=[
                    ('Content-Type', content_type),
                    ('Cache-Control', 'public, max-age=86400'),
                ]
            )
        
        # No image set - return empty response
        return request.make_response('', status=404)



    @http.route('/albirru_backend_theme/theme_settings', type='jsonrpc', auth='user')
    def get_theme_settings(self, **kwargs):
        """Get theme settings for current user/company"""
        config = request.env['albirru.theme.config'].get_current_config()
        return config.get_theme_values()

    def _coerce_and_validate(self, field, value):
        """Validate a settable field against FIELD_VALIDATORS.

        Returns:
            tuple: (coerced_value, error_message). error_message is None on success.
        """
        if field not in FIELD_VALIDATORS:
            return None, 'Invalid field'

        validator = FIELD_VALIDATORS[field]
        expected_type = validator['type']

        if expected_type == bool:
            value = bool(value)
        elif expected_type == int:
            try:
                value = int(value)
            except (ValueError, TypeError):
                return None, f'Invalid integer for {field}'
        elif expected_type == 'binary':
            # Accept a base64 string (upload) or False (clear the image)
            if value is False or value == '':
                value = False
            elif isinstance(value, str):
                error = self._validate_image_upload(value)
                if error:
                    return None, error
            else:
                return None, f'Invalid binary value for {field}'
        elif not isinstance(value, expected_type):
            return None, f'Invalid type for {field}'

        if 'values' in validator and value not in validator['values']:
            return None, f'Invalid value for {field}'

        if 'pattern' in validator and not re.match(validator['pattern'], str(value)):
            return None, f'Invalid format for {field}'

        if 'min' in validator and value < validator['min']:
            return None, f'{field} must be at least {validator["min"]}'
        if 'max' in validator and value > validator['max']:
            return None, f'{field} must be at most {validator["max"]}'

        return value, None

    @http.route('/albirru_backend_theme/save_setting', type='jsonrpc', auth='user')
    def save_setting(self, field, value, scope='user', **kwargs):
        """Save a theme setting.

        Three storage scopes exist:

        - dark_mode / sidebar_pinned are columns on res.users and always
          belong to the user.
        - scope='user' (the default) stores a personal override on res.users,
          layered on top of the company configuration. Any user may do this
          for themselves.
        - scope='company' writes the company default in albirru.theme.config
          and therefore requires administrator rights.

        Args:
            field: Field name to update
            value: New value for the field
            scope: 'user' or 'company'

        Returns:
            dict: Success status
        """
        user = request.env.user

        # Settings that are user-owned outright.
        if field in USER_OWNED_FIELDS:
            if user.save_albirru_user_setting(field, bool(value)):
                return {'success': True}
            return {'success': False, 'error': 'Failed to save user setting'}

        value, error = self._coerce_and_validate(field, value)
        if error:
            return {'success': False, 'error': error}

        if scope == 'company':
            # Applies to every user of the company - administrators only.
            if not user.has_group('base.group_system'):
                return {'success': False, 'error': 'Access denied'}

            # get_current_config() returns a sudo() recordset so that regular
            # users can read the theme. Drop back to the real user for the
            # write so the model ACL is enforced as a second line of defence.
            config = request.env['albirru.theme.config'].get_current_config().sudo(False)
            if not config.save_setting(field, value):
                return {'success': False, 'error': f'Invalid field {field}'}
            return {'success': True, 'scope': 'company'}

        # Personal override.
        if field in COMPANY_ONLY_FIELDS:
            return {
                'success': False,
                'error': f'{field} can only be set for the whole company.',
            }
        # Checked before the write so the client gets a message it can show,
        # instead of the generic "invalid field" the model would produce.
        if user.is_albirru_theme_locked():
            return {
                'success': False,
                'locked': True,
                'error': 'The theme is managed by your administrator.',
            }
        if not user.set_albirru_theme_override(field, value):
            return {'success': False, 'error': f'Invalid field {field}'}
        return {'success': True, 'scope': 'user'}

    @http.route('/albirru_backend_theme/reset_setting', type='jsonrpc', auth='user')
    def reset_setting(self, field=None, **kwargs):
        """Drop a personal override so the company default applies again.

        Args:
            field: the setting to reset, or None to reset every override

        Returns:
            dict: success status and the resulting effective settings
        """
        user = request.env.user
        if field is not None and field not in USER_OVERRIDABLE_FIELDS:
            return {'success': False, 'error': 'Invalid field'}

        user.clear_albirru_theme_override(field)
        return {
            'success': True,
            'settings': user.get_albirru_theme_settings(),
            'overridden': user.get_albirru_overridden_keys(),
        }

    @http.route('/albirru_backend_theme/search_records', type='jsonrpc', auth='user')
    def search_records(self, query, model='all', limit=15, **kwargs):
        """Search records across one or several models.

        Replaces the previous approach of firing one search_read per model from
        the browser. Doing it server-side means a single round trip, and lets us
        use name_search(), which honours each model's _rec_name instead of
        assuming every model has a 'name' field.

        Args:
            query: search terms
            model: a specific model name, or 'all' for the default model set
            limit: maximum number of results to return overall

        Returns:
            list: dicts with model, model_name, id and name
        """
        query = (query or '').strip()
        if not query:
            return []

        try:
            limit = max(1, min(int(limit), 50))
        except (ValueError, TypeError):
            limit = 15

        if model == 'all':
            models = self._get_searchable_models()
            per_model_limit = 3
        else:
            models = [model]
            per_model_limit = limit

        results = []
        for model_name in models:
            if len(results) >= limit:
                break
            # Model not installed, or the user may not read it
            if model_name not in request.env:
                continue
            Model = request.env[model_name]
            if not Model.has_access('read'):
                continue
            try:
                matches = Model.name_search(name=query, limit=per_model_limit)
            except Exception:
                # A model can refuse name_search (abstract rec_name, custom
                # override raising, ...) - skip it rather than fail the search.
                continue

            description = request.env['ir.model']._get(model_name).name or model_name
            for record_id, display_name in matches:
                results.append({
                    'model': model_name,
                    'model_name': description,
                    'id': record_id,
                    'name': display_name,
                })

        return results[:limit]

    def _get_searchable_models(self):
        """Default model set for the 'All Models' search.

        Only models actually present in the registry are returned, so the list
        adapts to the modules installed on the database.
        """
        candidates = [
            'res.partner',
            'hr.employee',
            'sale.order',
            'purchase.order',
            'crm.lead',
            'project.task',
            'project.project',
            'account.move',
            'product.product',
            'product.template',
            'stock.picking',
            'hr.department',
            'res.users',
        ]
        return [name for name in candidates if name in request.env]

    @http.route('/albirru_backend_theme/searchable_models', type='jsonrpc', auth='user')
    def searchable_models(self, **kwargs):
        """List the models offered in the search modal's model selector."""
        models = request.env['ir.model'].sudo().search_read(
            [('transient', '=', False)], ['name', 'model'], limit=200, order='name'
        )
        # Only expose models the current user is actually allowed to read.
        return [
            {'id': m['id'], 'name': m['name'], 'model': m['model']}
            for m in models
            if m['model'] in request.env
            and request.env[m['model']].has_access('read')
        ]

    @http.route('/albirru_backend_theme/bookmarks', type='jsonrpc', auth='user')
    def get_bookmarks(self, **kwargs):
        """Get user bookmarks"""
        user = request.env.user
        return user.albirru_bookmark_ids.get_bookmarks_data()

    @http.route('/albirru_backend_theme/add_bookmark', type='jsonrpc', auth='user')
    def add_bookmark(self, name, url, icon='fa-bookmark', **kwargs):
        """Add a new bookmark
        
        Args:
            name: Display name for the bookmark
            url: URL to bookmark (must be http/https or relative path)
            icon: FontAwesome icon class (default: fa-bookmark)
        
        Returns:
            dict: Success status and bookmark data
        """
        # Validate URL to prevent XSS attacks
        if not self._is_safe_url(url):
            return {'success': False, 'error': 'Invalid URL. Only http, https, or relative URLs are allowed.'}

        # The name is stored verbatim; every template renders it through t-esc,
        # which escapes at output time. Escaping here as well would corrupt the
        # stored value and display entities such as "&amp;" to the user.
        safe_name = name.strip()[:100] if name else 'Untitled'

        user = request.env.user
        bookmark = request.env['albirru.bookmark'].create({
            'name': safe_name,
            'url': url.strip(),
            'icon': icon if icon and icon.startswith('fa-') else 'fa-bookmark',
            'user_id': user.id,
        })
        return {
            'success': True,
            'bookmark': {
                'id': bookmark.id,
                'name': bookmark.name,
                'url': bookmark.url,
                'icon': bookmark.icon,
            }
        }

    @http.route('/albirru_backend_theme/remove_bookmark', type='jsonrpc', auth='user')
    def remove_bookmark(self, bookmark_id, **kwargs):
        """Remove a bookmark"""
        user = request.env.user
        bookmark = request.env['albirru.bookmark'].browse(bookmark_id)

        if bookmark.exists() and bookmark.user_id.id == user.id:
            bookmark.unlink()
            return {'success': True}

        return {'success': False, 'error': 'Bookmark not found'}

    @http.route('/albirru_backend_theme/app_groups', type='jsonrpc', auth='user')
    def get_app_groups(self, **kwargs):
        """Get app groups and menu data for App Drawer"""
        # Regular (non-sudo) access on both models so the ACL and the
        # multi-company record rule apply: a group belonging to another company
        # must not leak into this user's drawer.
        AppGroup = request.env['albirru.app.group']
        Menu = request.env['ir.ui.menu']

        # Get root menus (applications) that user has access to
        root_menus = Menu.search([
            ('parent_id', '=', False),
        ])
        accessible_root_ids = set(root_menus.ids)

        # Get all app groups sorted by sequence
        groups = AppGroup.search([], order='sequence, id')
        
        groups_data = []
        grouped_menu_ids = set()

        # Collect the root menus already claimed by a group visible to this
        # user. A group belonging to another company is not visible here, so
        # its menus correctly fall through to the ungrouped section.
        for group in groups:
            for menu in group.group_menu_list_ids:
                if not menu.parent_id:
                    grouped_menu_ids.add(menu.id)

        # Now build the display data for each group, respecting current user access
        for group in groups:
            group_menus = []
            # Only include menus the user has access to
            for menu in group.group_menu_list_ids:
                if not menu.parent_id and menu.id in accessible_root_ids:
                    group_menus.append(self._get_menu_data(menu))

            if group_menus:
                groups_data.append({
                    'id': group.id,
                    'name': group.name,
                    'sequence': group.sequence,
                    'use_group_icon': group.use_group_icon,
                    'group_icon_class_name': group.group_icon_class_name or '',
                    'has_group_icon': bool(group.group_menu_icon),
                    'menus': group_menus,
                })

        # Get ungrouped menus
        # Any root menu accessible to user that is NOT in any group
        ungrouped_menus = []
        for menu in root_menus:
            if menu.id not in grouped_menu_ids:
                # Include menu if it has an action or web_icon (standard app)
                # Some apps in Odoo 17+ might not have action directly at root
                if menu.action or menu.web_icon:
                    ungrouped_menus.append(self._get_menu_data(menu))

        return {
            'groups': groups_data,
            'ungrouped_menus': ungrouped_menus,
        }

    def _get_menu_data(self, menu):
        """Get menu data for frontend"""
        try:
            # Get xml_id properly
            xml_id_data = menu.get_external_id()
            xmlid = xml_id_data.get(menu.id, '') if xml_id_data else ''
            
            return {
                'id': menu.id,
                'name': menu.name,
                'action_id': menu.action.id if menu.action else None,
                'xmlid': xmlid,
                'web_icon': menu.web_icon or '',
                'use_icon': getattr(menu, 'use_icon', False),
                'icon_class_name': getattr(menu, 'icon_class_name', '') or '',
                'has_icon_img': bool(getattr(menu, 'icon_img', False)),
            }
        except Exception as e:
            _logger.error(f"Error getting menu data for menu {menu.id}: {e}")
            return {
                'id': menu.id,
                'name': menu.name,
                'action_id': menu.action.id if menu.action else None,
                'xmlid': '',
                'web_icon': menu.web_icon or '',
                'use_icon': False,
                'icon_class_name': '',
                'has_icon_img': False,
            }

