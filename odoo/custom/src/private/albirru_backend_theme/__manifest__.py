# -*- coding: utf-8 -*-
# Albirru Backend Theme for Odoo 19
{
    'name': 'Albirru Backend Theme',
    'category': 'Themes/Backend',
    'version': '19.0.1.0.2',
    'author': 'Albirru Solutions (Irwan Syah)',
    'maintainer': 'Albirru Solutions',
    'support': '1rw4n.5y4h1919@gmail.com',
    'website': 'https://www.albirru.com/',
    'live_test_url': 'https://demo.albirru.com',
    'images': [
        'static/description/banner.png',
        'static/description/dark_mode_view.png',
        'static/description/sidebar_view.png',
        'static/description/mobile_view.png',
        'static/description/app_drawer_view.png',
        'static/description/theme_settings_view.png',
        'static/description/global_search_view.png',
        'static/description/chatter_position_right.png',
        'static/description/chatter_position_bottom.png',
        'static/description/sticky_header_view.png',
        'static/description/slideshow.gif',
        'static/description/density_view.png',
    ],
    'summary': 'Free & open-source premium backend theme for Odoo 19: mobile-first, true dark mode, configurable sidebar, and enterprise-grade UI/UX. By Albirru Solutions.',
    'description': """
Albirru Backend Theme - Premium Odoo 19 Interface
=================================================

Elevate your Odoo interface with Albirru, a meticulously designed backend theme that focuses on user experience, speed, and aesthetic perfection.

Key Features
------------
*   **True Dark Mode**: scientifically calibrated for eye comfort.
*   **Mobile-First Design**: A native-app feel on smartphones and tablets.
*   **Advanced Navigation**: Choose between Vertical Sidebar or Horizontal Top Menu.
*   **Smart App Drawer**: Clutter-free app organization with categories.
*   **Global Search (Omni Search)**: Find menus, records, and contacts instantly (Ctrl+K).
*   **Customization**: Live theme customizer for fonts, colors, and density.
*   **Sticky Headers**: Keep list headers visible while scrolling.
*   **Chatter Position**: Optional right-sided chatter for wide screens.

Perfect for companies wanting a modern, enterprise-grade look for their Odoo Community or Enterprise edition.
    """,
    'depends': ['web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'security/albirru_security.xml',
        'data/theme_data.xml',
        'views/albirru_theme_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/albirru_app_group_views.xml',
        'views/menuitem.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # SCSS Variables (load first)
            'albirru_backend_theme/static/src/scss/variables.scss',

            # SCSS Components
            'albirru_backend_theme/static/src/scss/navbar.scss',
            'albirru_backend_theme/static/src/scss/sidebar.scss',
            'albirru_backend_theme/static/src/scss/form_view.scss',
            'albirru_backend_theme/static/src/scss/list_view.scss',
            'albirru_backend_theme/static/src/scss/kanban_view.scss',
            'albirru_backend_theme/static/src/scss/graph_pivot.scss',
            'albirru_backend_theme/static/src/scss/control_panel.scss',
            'albirru_backend_theme/static/src/scss/mail.scss',
            'albirru_backend_theme/static/src/scss/search_panel.scss',
            'albirru_backend_theme/static/src/scss/modal.scss',
            'albirru_backend_theme/static/src/scss/buttons.scss',
            'albirru_backend_theme/static/src/scss/responsive.scss',
            'albirru_backend_theme/static/src/scss/burger_menu.scss',
            'albirru_backend_theme/static/src/scss/search_modal.scss',
            'albirru_backend_theme/static/src/scss/app_drawer.scss',
            'albirru_backend_theme/static/src/scss/quick_settings.scss',
            'albirru_backend_theme/static/src/scss/loader.scss',
            'albirru_backend_theme/static/src/scss/menu_backgrounds.scss',
            # Colour transitions - applies in light mode too, so it must stay
            # out of the dark-only bundle.
            'albirru_backend_theme/static/src/scss/transitions.scss',

            # XML Templates
            'albirru_backend_theme/static/src/xml/navbar.xml',
            'albirru_backend_theme/static/src/xml/systray.xml',
            'albirru_backend_theme/static/src/xml/sidebar.xml',
            'albirru_backend_theme/static/src/xml/search_modal.xml',
            'albirru_backend_theme/static/src/xml/app_drawer.xml',
            'albirru_backend_theme/static/src/xml/quick_settings.xml',

            # JavaScript - Theme Service (load first)
            'albirru_backend_theme/static/src/js/theme_service.js',
            'albirru_backend_theme/static/src/js/menu_service_patch.js',

            # JavaScript - Components
            'albirru_backend_theme/static/src/js/sidebar.js',
            'albirru_backend_theme/static/src/js/search_modal.js',
            'albirru_backend_theme/static/src/js/fullscreen.js',
            'albirru_backend_theme/static/src/js/app_drawer.js',
            'albirru_backend_theme/static/src/js/quick_settings.js',
            'albirru_backend_theme/static/src/js/dark_mode_toggle.js',

            # JavaScript - Patches (load last)
            'albirru_backend_theme/static/src/js/form_renderer_patch.js',
            'albirru_backend_theme/static/src/js/navbar_patch.js',
            'albirru_backend_theme/static/src/js/webclient_patch.js',
        ],
        # Dark mode styling. Odoo serves this bundle instead of web.assets_web
        # when ir.http.color_scheme() returns 'dark', so light-mode users never
        # download it. It is listed last, after every core stylesheet, which is
        # what lets the overrides win on source order.
        'web.assets_web_dark': [
            'albirru_backend_theme/static/src/scss/dark_mode.scss',
        ],

        # Login styling is pulled in by the login layout template only, so it is
        # not shipped with every public website page.
        'albirru_backend_theme.assets_login': [
            'albirru_backend_theme/static/src/scss/variables.scss',
            'albirru_backend_theme/static/src/scss/login.scss',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
