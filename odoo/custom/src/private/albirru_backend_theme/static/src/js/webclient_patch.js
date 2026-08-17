/** @odoo-module **/
// Albirru Backend Theme - WebClient Patch
// Compatible with Odoo 19

import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Patch WebClient to initialize theme and handle favicon/tab name
 */
patch(WebClient.prototype, {
    setup() {
        super.setup();

        if (!session.albirru_theme_installed) {
            return;
        }

        try {
            this.albirruTheme = useService("albirruTheme");
        } catch (e) {
            console.warn('Albirru theme service not available in WebClient');
        }

        onMounted(() => {
            this._initAlbirruTheme();
        });

        onWillUnmount(() => {
            this._cleanupAlbirruTheme();
        });
    },

    /**
     * Show the App Drawer instead of auto-loading the first application, when
     * the company enabled that behaviour.
     *
     * @override
     */
    async _loadDefaultApp() {
        const settings = this.albirruTheme?.getSettings() || {};
        if (this.albirruTheme && settings.open_drawer_on_home !== false) {
            this.albirruTheme.openAppDrawer();
            return;
        }
        return super._loadDefaultApp(...arguments);
    },

    /**
     * Initialize Albirru theme
     */
    _initAlbirruTheme() {
        const settings = session.albirru_theme_settings || {};
        const branding = session.albirru_branding || {};

        // Branding and favicon are still handled here as they relate to web client
        // theme_service handles the DOM attributes (data-albirru-*)

        // Set tab name
        if (branding.tab_name) {
            this._setTabName(branding.tab_name);
        }

        // Set favicon
        if (branding.has_favicon) {
            this._setFavicon();
        }

        // Sidebar and body classes
        const body = document.body;
        body.classList.add("albirru-theme-active");

        if (settings.sidebar_position === "left") {
            body.classList.add("albirru-sidebar-left");
        }

        if (!settings.sidebar_pinned) {
            body.classList.add("albirru-sidebar-collapsed");
        }

        // Listen for title changes to maintain branding
        const titleElement = document.querySelector("title");
        if (titleElement) {
            this._titleObserver = new MutationObserver(() => {
                if (branding.tab_name) {
                    this._setTabName(branding.tab_name);
                }
            });

            this._titleObserver.observe(titleElement, {
                childList: true,
                characterData: true,
                subtree: true,
            });
        }
    },

    /**
     * Set browser tab name
     */
    _setTabName(name) {
        const currentTitle = document.title;
        const separator = " - ";

        // Don't modify if already has branding
        if (currentTitle.endsWith(separator + name)) {
            return;
        }

        // Remove old branding and add new
        let baseTitle = currentTitle;
        const lastSeparator = currentTitle.lastIndexOf(separator);
        if (lastSeparator > 0) {
            baseTitle = currentTitle.substring(0, lastSeparator);
        }

        document.title = baseTitle + separator + name;
    },

    /**
     * Set favicon from company settings
     */
    _setFavicon() {
        // Favicon is served from controller
        let link = document.querySelector("link[rel~='icon']");
        if (!link) {
            link = document.createElement("link");
            link.rel = "icon";
            document.head.appendChild(link);
        }
        link.href = "/albirru_backend_theme/favicon";
    },

    /**
     * Cleanup theme
     */
    _cleanupAlbirruTheme() {
        if (this._titleObserver) {
            this._titleObserver.disconnect();
        }
    },
});
