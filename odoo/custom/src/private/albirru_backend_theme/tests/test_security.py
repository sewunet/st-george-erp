# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, HttpCase, tagged

from ..controllers.main import AlbirruThemeController, MAX_IMAGE_SIZE

# Smallest valid payloads for the formats we accept.
PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


@tagged('post_install', '-at_install')
class TestSettingAccess(TransactionCase):
    """Company-wide theme settings must not be writable by regular users."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['res.users'].create({
            'name': 'Albirru Employee',
            'login': 'albirru_employee',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def test_employee_cannot_write_company_config(self):
        """The ACL alone must stop a non-admin write, without the controller."""
        config = self.env['albirru.theme.config'].get_current_config()
        # with_user() already drops superuser mode (models.py:5988).
        as_employee = config.with_user(self.employee)

        with self.assertRaises(AccessError):
            as_employee.save_setting('color_scheme', 'scheme_9')

    def test_employee_can_read_company_config(self):
        """Reading must still work - every user needs the theme to render."""
        config = self.env['albirru.theme.config'].get_current_config()
        as_employee = config.with_user(self.employee)

        self.assertTrue(as_employee.color_scheme)

    def test_employee_can_change_own_preferences(self):
        """User-level settings stay self-serviceable."""
        employee = self.employee.with_user(self.employee)

        self.assertTrue(employee.save_albirru_user_setting('dark_mode', True))
        self.assertTrue(employee.albirru_dark_mode)

    def test_save_user_setting_rejects_company_fields(self):
        """The user-level helper must not be a back door to other fields."""
        employee = self.employee.with_user(self.employee)

        self.assertFalse(employee.save_albirru_user_setting('color_scheme', 'scheme_9'))


@tagged('post_install', '-at_install')
class TestImageUploadValidation(TransactionCase):
    """Uploaded backgrounds are served back to browsers - validate them."""

    def setUp(self):
        super().setUp()
        self.controller = AlbirruThemeController()

    def test_accepts_valid_png(self):
        payload = base64.b64encode(PNG_1PX).decode()
        self.assertIsNone(self.controller._validate_image_upload(payload))

    def test_rejects_non_image_payload(self):
        payload = base64.b64encode(b'<?php system($_GET["c"]); ?>').decode()
        error = self.controller._validate_image_upload(payload)

        self.assertTrue(error)
        self.assertIn('Unsupported image format', error)

    def test_rejects_malformed_base64(self):
        error = self.controller._validate_image_upload('this is not base64!!')

        self.assertTrue(error)
        self.assertIn('Invalid image data', error)

    def test_rejects_oversized_image(self):
        # A valid PNG header followed by enough padding to exceed the limit.
        oversized = PNG_1PX + b'\x00' * (MAX_IMAGE_SIZE + 1)
        error = self.controller._validate_image_upload(
            base64.b64encode(oversized).decode()
        )

        self.assertTrue(error)
        self.assertIn('too large', error)


@tagged('post_install', '-at_install')
class TestSaveSettingEndpoint(HttpCase):
    """End-to-end check of the /save_setting authorisation guard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.users'].create({
            'name': 'Albirru Endpoint User',
            'login': 'albirru_endpoint',
            'password': 'albirru_endpoint',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def test_non_admin_is_denied(self):
        """A logged-in employee must not be able to restyle the whole company."""
        self.authenticate('albirru_endpoint', 'albirru_endpoint')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'company'},
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Access denied')

    def test_non_admin_can_set_own_dark_mode(self):
        """User-level settings remain available to everyone."""
        self.authenticate('albirru_endpoint', 'albirru_endpoint')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'dark_mode', 'value': True},
        )

        self.assertTrue(result['success'])

    def test_admin_is_allowed(self):
        self.authenticate('admin', 'admin')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'company'},
        )

        self.assertTrue(result['success'])
        self.assertEqual(
            self.env['albirru.theme.config'].get_current_config().color_scheme,
            'scheme_9',
        )

    def test_unknown_field_is_rejected(self):
        self.authenticate('admin', 'admin')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'name', 'value': 'hacked', 'scope': 'company'},
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid field')

    def test_out_of_range_value_is_rejected(self):
        self.authenticate('admin', 'admin')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'menu_bg_opacity', 'value': 500},
        )

        self.assertFalse(result['success'])
