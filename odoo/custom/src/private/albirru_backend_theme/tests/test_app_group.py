# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAppGroup(TransactionCase):
    """App groups organise root menus in the drawer and the sidebar."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Group = cls.env['albirru.app.group']
        cls.menu_a = cls.env['ir.ui.menu'].create({'name': 'Albirru Test App A'})
        cls.menu_b = cls.env['ir.ui.menu'].create({'name': 'Albirru Test App B'})

    def test_menu_belongs_to_a_single_group(self):
        """The One2many is backed by a FK, so reassignment is exclusive."""
        first = self.Group.create({'name': 'First', 'group_menu_list_ids': [(6, 0, [self.menu_a.id])]})
        second = self.Group.create({'name': 'Second'})

        second.group_menu_list_ids = [(6, 0, [self.menu_a.id])]

        self.assertEqual(self.menu_a.albirru_app_group_id, second)
        self.assertNotIn(self.menu_a, first.group_menu_list_ids)

    def test_onchange_warns_when_stealing_a_menu(self):
        """Moving a menu between groups must warn rather than fail silently."""
        origin = self.Group.create({
            'name': 'Origin',
            'group_menu_list_ids': [(6, 0, [self.menu_b.id])],
        })
        target = self.Group.create({'name': 'Target'})

        form = self.env['albirru.app.group'].new(
            {'name': 'Target', 'group_menu_list_ids': [(6, 0, [self.menu_b.id])]},
            origin=target,
        )
        result = form._onchange_group_menu_list_ids()

        self.assertTrue(result, 'Expected a warning payload.')
        self.assertIn('warning', result)
        self.assertIn(origin.name, result['warning']['message'])

    def test_onchange_silent_for_unassigned_menus(self):
        """No warning when nothing is being taken from another group."""
        free_menu = self.env['ir.ui.menu'].create({'name': 'Albirru Free App'})
        group = self.Group.create({'name': 'Fresh'})

        form = self.env['albirru.app.group'].new(
            {'name': 'Fresh', 'group_menu_list_ids': [(6, 0, [free_menu.id])]},
            origin=group,
        )

        self.assertFalse(form._onchange_group_menu_list_ids())

    def test_groups_are_ordered_by_sequence(self):
        self.Group.create({'name': 'Zeta', 'sequence': 1})
        self.Group.create({'name': 'Alpha', 'sequence': 99})
        names = self.Group.search([('name', 'in', ['Zeta', 'Alpha'])]).mapped('name')

        self.assertEqual(names, ['Zeta', 'Alpha'])
