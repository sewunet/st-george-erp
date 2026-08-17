# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestThemeConfig(TransactionCase):
    """Configuration lifecycle: creation, uniqueness and read-only lookup."""

    def test_get_current_config_is_idempotent(self):
        """Repeated calls must return the same record, not create duplicates."""
        Config = self.env['albirru.theme.config']
        first = Config.get_current_config()
        second = Config.get_current_config()

        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(
            Config.sudo().search_count([('company_id', '=', self.env.company.id)]),
            1,
            'get_current_config() must not create a second configuration.',
        )

    def test_get_display_config_never_creates(self):
        """The read-only lookup must not write, even when nothing exists yet."""
        Config = self.env['albirru.theme.config']
        company = self.env['res.company'].create({'name': 'Albirru Test Co'})
        Config_company = Config.with_company(company)

        self.assertFalse(
            Config_company.get_display_config(),
            'A company without configuration must yield an empty recordset.',
        )
        self.assertEqual(
            Config.sudo().search_count([('company_id', '=', company.id)]),
            0,
            'get_display_config() must not create a configuration.',
        )

    def test_display_config_fields_are_falsy_when_empty(self):
        """Templates rely on field access on an empty recordset being falsy."""
        company = self.env['res.company'].create({'name': 'Albirru Empty Co'})
        config = self.env['albirru.theme.config'].with_company(company).get_display_config()

        self.assertFalse(config.color_scheme)
        self.assertEqual(config.color_scheme or 'scheme_1', 'scheme_1')

    def test_only_one_config_per_company(self):
        """A second configuration for the same company must be refused."""
        Config = self.env['albirru.theme.config']
        Config.get_current_config()

        with self.assertRaises(UserError):
            Config.sudo().create({
                'name': 'Duplicate',
                'company_id': self.env.company.id,
            })

    def test_save_setting_rejects_unknown_field(self):
        """Only real fields may be written; method names must be refused."""
        config = self.env['albirru.theme.config'].get_current_config()

        self.assertFalse(config.save_setting('unlink', True))
        self.assertFalse(config.save_setting('no_such_field', 'x'))
        self.assertTrue(config.save_setting('color_scheme', 'scheme_5'))
        self.assertEqual(config.color_scheme, 'scheme_5')

    def test_theme_values_exclude_user_level_settings(self):
        """dark_mode / sidebar_pinned belong to res.users, not to the company."""
        values = self.env['albirru.theme.config'].get_current_config().get_theme_values()

        self.assertNotIn('dark_mode', values)
        self.assertNotIn('sidebar_pinned', values)
        self.assertIn('color_scheme', values)
        self.assertIn('open_drawer_on_home', values)

    def test_user_settings_override_company_values(self):
        """The merged payload must carry the user's own preferences."""
        user = self.env.user
        user.albirru_dark_mode = True
        user.albirru_sidebar_pinned = False

        settings = user.get_albirru_theme_settings()

        self.assertTrue(settings['dark_mode'])
        self.assertFalse(settings['sidebar_pinned'])

    def test_color_scheme_follows_user_preference(self):
        """ir.http.color_scheme() drives which asset bundle Odoo serves."""
        IrHttp = self.env['ir.http']
        self.env.user.albirru_dark_mode = False
        self.assertEqual(IrHttp.color_scheme(), 'light')

        self.env.user.albirru_dark_mode = True
        self.assertEqual(IrHttp.color_scheme(), 'dark')
