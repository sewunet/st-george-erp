/** @odoo-module **/
// Albirru Backend Theme - Dark Mode Toggle Component
// Compatible with Odoo 19

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

/**
 * Dark Mode Toggle Component for Systray
 */
export class AlbirruDarkModeToggle extends Component {
    static template = "albirru_backend_theme.DarkModeToggle";
    static props = {};

    setup() {
        this.albirruTheme = useService("albirruTheme");

        this.state = useState({
            isDarkMode: this.albirruTheme.isDarkMode(),
        });

        // Listen for theme changes
        this.albirruTheme.bus.addEventListener('THEME_CHANGED', (ev) => {
            if (ev.detail.setting === 'dark_mode') {
                this.state.isDarkMode = ev.detail.value;
            }
        });
    }

    /**
     * Toggle dark mode
     */
    async onToggle() {
        await this.albirruTheme.toggleDarkMode();
    }

    /**
     * Get icon class based on current mode
     */
    get iconClass() {
        return this.state.isDarkMode ? 'fa-sun-o' : 'fa-moon-o';
    }

    /**
     * Get tooltip text
     */
    get tooltipText() {
        return this.state.isDarkMode ? _t("Switch to Light Mode") : _t("Switch to Dark Mode");
    }
}

/**
 * Bookmark Button Component for Systray
 */
export class AlbirruBookmarkButton extends Component {
    static template = "albirru_backend_theme.BookmarkButton";
    static props = {};

    setup() {
        this.albirruTheme = useService("albirruTheme");

        this.state = useState({
            bookmarks: this.albirruTheme.getBookmarks(),
            showDropdown: false,
        });

        // Listen for bookmark changes
        this.albirruTheme.bus.addEventListener('BOOKMARKS_CHANGED', (ev) => {
            this.state.bookmarks = ev.detail.bookmarks;
        });
    }

    /**
     * Toggle dropdown visibility
     */
    toggleDropdown() {
        this.state.showDropdown = !this.state.showDropdown;
    }

    /**
     * Add current page as bookmark
     */
    async onAddBookmark() {
        // webclient_patch appends " - <tab_name>" to the document title; strip
        // that suffix so the bookmark keeps only the page name.
        const suffix = ` - ${this.albirruTheme.getBranding().tab_name || ""}`;
        let name = document.title;
        if (suffix.length > 3 && name.endsWith(suffix)) {
            name = name.slice(0, -suffix.length);
        }
        const url = window.location.href;

        try {
            await this.albirruTheme.addBookmark(name, url);
        } catch (error) {
            console.error('Failed to add bookmark:', error);
        }
    }

    /**
     * Navigate to bookmark
     */
    onBookmarkClick(bookmark) {
        window.location.href = bookmark.url;
        this.state.showDropdown = false;
    }

    /**
     * Remove bookmark
     */
    async onRemoveBookmark(bookmarkId, ev) {
        ev.stopPropagation();
        await this.albirruTheme.removeBookmark(bookmarkId);
    }
}

/**
 * Sidebar Toggle Component for Systray
 */
export class AlbirruSidebarToggle extends Component {
    static template = "albirru_backend_theme.SidebarToggle";
    static props = {};

    setup() {
        this.albirruTheme = useService("albirruTheme");

        this.state = useState({
            isPinned: this.albirruTheme.isSidebarPinned(),
        });

        // Listen for theme changes
        this.albirruTheme.bus.addEventListener('THEME_CHANGED', (ev) => {
            if (ev.detail.setting === 'sidebar_pinned') {
                this.state.isPinned = ev.detail.value;
            }
        });
    }

    /**
     * Toggle sidebar pinned state
     */
    async onToggle() {
        await this.albirruTheme.toggleSidebarPinned();
    }

    /**
     * Get icon class
     */
    get iconClass() {
        return this.state.isPinned ? 'fa-thumb-tack' : 'fa-thumb-tack fa-rotate-90';
    }

    /**
     * Get tooltip text
     */
    get tooltipText() {
        return this.state.isPinned ? _t("Collapse Sidebar") : _t("Pin Sidebar");
    }
}

// Register systray items only if theme is installed
if (session.albirru_theme_installed) {
    const systrayRegistry = registry.category("systray");

    // Dark Mode Toggle - Odoo 19 uses simple { Component } format
    systrayRegistry.add("albirru.DarkModeToggle", {
        Component: AlbirruDarkModeToggle,
    }, { sequence: 5 });

    // Bookmark Button
    systrayRegistry.add("albirru.BookmarkButton", {
        Component: AlbirruBookmarkButton,
    }, { sequence: 6 });

    // Sidebar Toggle - Removed from systray per user request
    // Users can use the pin button in the sidebar header instead
    // systrayRegistry.add("albirru.SidebarToggle", {
    //     Component: AlbirruSidebarToggle,
    // }, { sequence: 7 });
}
