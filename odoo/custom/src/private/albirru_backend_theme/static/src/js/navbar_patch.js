/** @odoo-module **/
// Albirru Backend Theme - NavBar Patch
// Compatible with Odoo 19

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { onMounted, onWillUnmount, useState } from "@odoo/owl";

/**
 * Patch NavBar to add Albirru theme functionality
 */
patch(NavBar.prototype, {
    setup() {
        super.setup();

        // Only initialize if theme is installed
        if (!session.albirru_theme_installed) {
            return;
        }

        // Get theme service
        try {
            this.albirruTheme = useService("albirruTheme");
        } catch (e) {
            console.warn('Albirru theme service not available');
            return;
        }

        // Theme state
        this.albirruState = useState({
            isDarkMode: this.albirruTheme.isDarkMode(),
            isSidebarPinned: this.albirruTheme.isSidebarPinned(),
            bookmarks: this.albirruTheme.getBookmarks(),
            faviconFailed: false,
            sidebarPosition: this.albirruTheme.getSettings().sidebar_position || 'left',
        });

        // Bind handlers once for proper cleanup
        this._boundOnThemeChanged = this._onThemeChanged.bind(this);
        this._boundOnBookmarksChanged = this._onBookmarksChanged.bind(this);

        // Listen for theme changes
        this.albirruTheme.bus.addEventListener('THEME_CHANGED', this._boundOnThemeChanged);
        this.albirruTheme.bus.addEventListener('BOOKMARKS_CHANGED', this._boundOnBookmarksChanged);

        onMounted(() => {
            this._initAlbirruTheme();
            this._setupAppDrawerTrigger();
        });

        onWillUnmount(() => {
            if (this.albirruTheme) {
                this.albirruTheme.bus.removeEventListener('THEME_CHANGED', this._boundOnThemeChanged);
                this.albirruTheme.bus.removeEventListener('BOOKMARKS_CHANGED', this._boundOnBookmarksChanged);
            }
            this._cleanupAppDrawerTrigger();
        });
    },

    /**
     * Initialize theme on mount
     */
    _initAlbirruTheme() {
        // Add theme class to web client
        const webClient = document.querySelector('.o_web_client');
        if (webClient) {
            webClient.classList.add('albirru-theme-active');

            // Apply sidebar position class
            const settings = this.albirruTheme.getSettings();
            if (settings.sidebar_position === 'left') {
                webClient.classList.add('albirru-sidebar-left');
            }
        }

        // NOTE: the browser tab name is owned by webclient_patch.js.
        // Do not set it here as well - two patches writing document.title with
        // different separators makes the branding accumulate.
    },

    /**
     * Handle theme change events
     */
    _onThemeChanged(ev) {
        const { setting, value } = ev.detail;

        if (setting === 'dark_mode') {
            this.albirruState.isDarkMode = value;
        } else if (setting === 'sidebar_pinned') {
            this.albirruState.isSidebarPinned = value;
        } else if (setting === 'sidebar_position') {
            // Drives whether the navbar shows its own apps menu.
            this.albirruState.sidebarPosition = value;
        }
    },

    /**
     * Handle bookmarks change events
     */
    _onBookmarksChanged(ev) {
        this.albirruState.bookmarks = ev.detail.bookmarks;
    },

    /**
     * Toggle dark mode
     */
    async onToggleDarkMode() {
        if (this.albirruTheme) {
            await this.albirruTheme.toggleDarkMode();
        }
    },

    /**
     * Toggle sidebar pinned state
     */
    async onToggleSidebarPinned() {
        if (this.albirruTheme) {
            await this.albirruTheme.toggleSidebarPinned();
        }
    },

    /**
     * Add current page as bookmark
     */
    async onAddBookmark() {
        if (!this.albirruTheme) return;

        const currentApp = this.menuService.getCurrentApp();
        const name = currentApp ? currentApp.name : document.title;
        const url = window.location.href;

        try {
            await this.albirruTheme.addBookmark(name, url);
        } catch (error) {
            console.error('Failed to add bookmark:', error);
        }
    },

    /**
     * Navigate to bookmark
     */
    onBookmarkClick(bookmark) {
        window.location.href = bookmark.url;
    },

    /**
     * Remove bookmark
     */
    async onRemoveBookmark(bookmarkId, ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (this.albirruTheme) {
            await this.albirruTheme.removeBookmark(bookmarkId);
        }
    },

    /**
     * Fall back to the icon when the company favicon cannot be loaded.
     */
    onAlbirruFaviconError() {
        this.albirruState.faviconFailed = true;
    },

    get albirruFaviconFailed() {
        return this.albirruState?.faviconFailed ?? false;
    },

    /**
     * Check if Albirru theme is active
     */
    get isAlbirruThemeActive() {
        return !!session.albirru_theme_installed;
    },

    /**
     * Get sidebar position from settings
     */
    get sidebarPosition() {
        // Read from reactive state so the navbar re-renders when the user
        // switches menu position, instead of needing a page reload.
        return this.albirruState?.sidebarPosition || 'left';
    },

    /**
     * Get branding info
     */
    get branding() {
        if (!this.albirruTheme) return {};
        return this.albirruTheme.getBranding();
    },

    /**
     * Get session data for company ID
     */
    get session() {
        return session;
    },

    /**
     * Get current company ID
     */
    get companyId() {
        return session.user_companies?.current_company || session.company_id || 1;
    },

    /**
     * Open App Drawer on mobile (App Switcher button)
     */
    onMobileAppSwitcher() {
        // Open App Drawer via theme service
        if (this.albirruTheme) {
            this.albirruTheme.openAppDrawer();
        }
    },

    /**
     * Toggle mobile sidebar (hamburger menu for Top Menu position)
     * Opens Odoo's native burger menu
     */
    onMobileMenuToggle() {
        // Find and click Odoo's native (hidden) burger menu toggle
        const nativeBurger = document.querySelector('.o_menu_toggle');
        if (nativeBurger) {
            nativeBurger.click();
        } else {
            // Fallback: dispatch event for sidebar component
            this.env.bus.trigger("ALBIRRU:TOGGLE-MOBILE-SIDEBAR");
        }
    },

    /**
     * Setup App Drawer trigger on apps menu button
     */
    _setupAppDrawerTrigger() {
        // Find the apps menu toggle button (the grid icon in navbar)
        const appsMenuToggle = document.querySelector('.o_navbar_apps_menu .dropdown-toggle, .o_navbar_apps_menu > a');

        if (appsMenuToggle && this.albirruTheme) {
            // Store reference to original click handler
            this._appsMenuToggle = appsMenuToggle;

            // Create bound handler
            this._boundAppDrawerHandler = (ev) => {
                ev.preventDefault();
                ev.stopPropagation();

                // Close any open Bootstrap dropdowns
                const openDropdown = document.querySelector('.o_navbar_apps_menu.show, .o_navbar_apps_menu .dropdown-menu.show');
                if (openDropdown) {
                    openDropdown.classList.remove('show');
                }

                // Open our custom App Drawer via theme service
                this.albirruTheme.openAppDrawer();
            };

            // Add click handler
            appsMenuToggle.addEventListener('click', this._boundAppDrawerHandler, true);
        }
    },

    /**
     * Cleanup App Drawer trigger
     */
    _cleanupAppDrawerTrigger() {
        if (this._appsMenuToggle && this._boundAppDrawerHandler) {
            this._appsMenuToggle.removeEventListener('click', this._boundAppDrawerHandler, true);
        }
    },
});
