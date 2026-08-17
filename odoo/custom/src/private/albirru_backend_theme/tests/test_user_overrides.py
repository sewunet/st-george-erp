# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, HttpCase, tagged


@tagged('post_install', '-at_install')
class TestUserOverrides(TransactionCase):
    """Personal preferences layer on top of the company configuration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['res.users'].create({
            'name': 'Albirru Override User',
            'login': 'albirru_override',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.config = cls.env['albirru.theme.config'].get_current_config()
        cls.config.color_scheme = 'scheme_3'
        cls.config.font_size = 'medium'

    def test_without_override_company_default_applies(self):
        settings = self.employee.get_albirru_theme_settings()

        self.assertEqual(settings['color_scheme'], 'scheme_3')
        self.assertEqual(self.employee.get_albirru_overridden_keys(), [])

    def test_override_wins_over_company_default(self):
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        settings = self.employee.get_albirru_theme_settings()

        self.assertEqual(settings['color_scheme'], 'scheme_7')
        self.assertEqual(settings['font_size'], 'medium', 'Untouched keys must still follow the company.')
        self.assertEqual(self.employee.get_albirru_overridden_keys(), ['color_scheme'])

    def test_override_does_not_affect_other_users(self):
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        other = self.env['res.users'].create({
            'name': 'Albirru Other User',
            'login': 'albirru_other',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        self.assertEqual(
            other.get_albirru_theme_settings()['color_scheme'], 'scheme_3'
        )

    def test_company_only_fields_cannot_be_overridden(self):
        self.assertFalse(
            self.employee.set_albirru_theme_override('menu_background', 'x')
        )
        self.assertFalse(
            self.employee.set_albirru_theme_override('menu_bg_opacity', 50)
        )

    def test_clear_single_override(self):
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        self.employee.set_albirru_theme_override('font_size', 'large')

        self.assertTrue(self.employee.clear_albirru_theme_override('color_scheme'))

        settings = self.employee.get_albirru_theme_settings()
        self.assertEqual(settings['color_scheme'], 'scheme_3', 'Back to the company default.')
        self.assertEqual(settings['font_size'], 'large', 'Other overrides survive.')

    def test_clear_all_overrides(self):
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        self.employee.set_albirru_theme_override('font_size', 'large')

        self.assertTrue(self.employee.clear_albirru_theme_override())

        settings = self.employee.get_albirru_theme_settings()
        self.assertEqual(settings['color_scheme'], 'scheme_3')
        self.assertEqual(settings['font_size'], 'medium')
        self.assertEqual(self.employee.get_albirru_overridden_keys(), [])

    def test_clear_is_a_noop_when_nothing_set(self):
        self.assertFalse(self.employee.clear_albirru_theme_override())
        self.assertFalse(self.employee.clear_albirru_theme_override('color_scheme'))

    def test_user_can_write_own_overrides(self):
        """A plain employee must be able to personalise without extra rights."""
        as_self = self.employee.with_user(self.employee)

        self.assertTrue(as_self.set_albirru_theme_override('font_size', 'large'))
        self.assertEqual(
            as_self.get_albirru_theme_settings()['font_size'], 'large'
        )


@tagged('post_install', '-at_install')
class TestThemeScope(TransactionCase):
    """A company may keep the theme to itself instead of letting users choose."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['res.users'].create({
            'name': 'Albirru Scope Employee',
            'login': 'albirru_scope_employee',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.config = cls.env['albirru.theme.config'].get_current_config()
        cls.config.color_scheme = 'scheme_3'

    def test_default_scope_is_per_user(self):
        self.assertEqual(self.config.theme_scope, 'user')
        self.assertFalse(self.employee.is_albirru_theme_locked())

    def test_locked_scope_ignores_existing_overrides(self):
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        self.config.theme_scope = 'company'

        settings = self.employee.get_albirru_theme_settings()
        self.assertEqual(settings['color_scheme'], 'scheme_3')
        self.assertEqual(self.employee.get_albirru_overridden_keys(), [])

    def test_locked_scope_keeps_overrides_for_later(self):
        """Locking must not destroy what users configured for themselves."""
        self.employee.set_albirru_theme_override('color_scheme', 'scheme_7')
        self.config.theme_scope = 'company'
        self.config.theme_scope = 'user'

        self.assertEqual(
            self.employee.get_albirru_theme_settings()['color_scheme'], 'scheme_7'
        )

    def test_locked_scope_refuses_new_overrides(self):
        self.config.theme_scope = 'company'

        self.assertFalse(
            self.employee.set_albirru_theme_override('font_size', 'large')
        )
        self.assertFalse(self.employee.albirru_theme_overrides)

    def test_dark_mode_survives_a_locked_theme(self):
        """The one preference a locked company must not take away."""
        self.config.theme_scope = 'company'
        self.employee.save_albirru_user_setting('dark_mode', True)

        settings = self.employee.get_albirru_theme_settings()
        self.assertTrue(settings['dark_mode'])
        self.assertTrue(self.employee.is_albirru_theme_locked())

    def test_config_settings_writes_the_scope(self):
        settings = self.env['res.config.settings'].create({})
        self.assertEqual(settings.albirru_theme_scope, 'user')

        settings.albirru_theme_scope = 'company'
        settings.execute()

        self.assertEqual(
            self.env['albirru.theme.config'].get_current_config().theme_scope,
            'company',
        )


@tagged('post_install', '-at_install')
class TestOverrideEndpoints(HttpCase):
    """The save/reset endpoints must separate personal and company scope."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.users'].create({
            'name': 'Albirru Scope User',
            'login': 'albirru_scope',
            'password': 'albirru_scope',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.env['albirru.theme.config'].get_current_config().color_scheme = 'scheme_2'

    def test_employee_can_save_personal_override(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'user'},
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['scope'], 'user')

        user = self.env['res.users'].search([('login', '=', 'albirru_scope')])
        self.assertEqual(user.albirru_theme_overrides.get('color_scheme'), 'scheme_9')
        self.assertEqual(
            self.env['albirru.theme.config'].get_current_config().color_scheme,
            'scheme_2',
            'A personal override must not touch the company configuration.',
        )

    def test_employee_still_denied_company_scope(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'company'},
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Access denied')

    def test_company_only_field_rejected_at_user_scope(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'menu_bg_opacity', 'value': 40, 'scope': 'user'},
        )

        self.assertFalse(result['success'])
        self.assertIn('whole company', result['error'])

    def test_invalid_value_rejected_before_storage(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_999', 'scope': 'user'},
        )

        self.assertFalse(result['success'])

    def test_reset_restores_company_default(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'user'},
        )
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/reset_setting', {'field': 'color_scheme'}
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['settings']['color_scheme'], 'scheme_2')
        self.assertEqual(result['overridden'], [])

    def test_reset_rejects_unknown_field(self):
        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/reset_setting', {'field': 'not_a_setting'}
        )

        self.assertFalse(result['success'])

    def test_locked_theme_rejects_personal_override(self):
        config = self.env['albirru.theme.config'].get_current_config()
        config.theme_scope = 'company'
        self.env.flush_all()
        self.addCleanup(config.write, {'theme_scope': 'user'})

        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'color_scheme', 'value': 'scheme_9', 'scope': 'user'},
        )

        self.assertFalse(result['success'])
        self.assertTrue(result['locked'])

    def test_locked_theme_still_allows_dark_mode(self):
        config = self.env['albirru.theme.config'].get_current_config()
        config.theme_scope = 'company'
        self.env.flush_all()
        self.addCleanup(config.write, {'theme_scope': 'user'})

        self.authenticate('albirru_scope', 'albirru_scope')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'dark_mode', 'value': True},
        )

        self.assertTrue(result['success'])
        user = self.env['res.users'].search([('login', '=', 'albirru_scope')])
        self.assertTrue(user.albirru_dark_mode)

    def test_theme_scope_is_not_writable_through_the_endpoint(self):
        """Even an administrator must go through General Settings for this."""
        self.authenticate('admin', 'admin')
        result = self.make_jsonrpc_request(
            '/albirru_backend_theme/save_setting',
            {'field': 'theme_scope', 'value': 'company', 'scope': 'company'},
        )

        self.assertFalse(result['success'])
        self.assertEqual(
            self.env['albirru.theme.config'].get_current_config().theme_scope,
            'user',
        )
