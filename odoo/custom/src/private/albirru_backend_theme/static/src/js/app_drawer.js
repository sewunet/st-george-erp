/** @odoo-module **/
// Albirru Backend Theme - App Drawer Component
// Compatible with Odoo 19

import { Component, useState, useRef, useEffect, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { fuzzyLookup } from "@web/core/utils/search";

/**
 * App Drawer Component
 * Full-screen app launcher with search and app groups support
 */
export class AlbirruAppDrawer extends Component {
    static template = "albirru_backend_theme.AppDrawer";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.ui = useService("ui");

        // Get theme service for event communication
        try {
            this.themeService = useService("albirruTheme");
        } catch (e) {
            console.warn('Albirru theme service not available for App Drawer');
        }

        this.searchRef = useRef("searchInput");
        this.dialogRef = useRef("dialog");

        // Move focus into the drawer once it is rendered; the search input when
        // there is one, otherwise the dialog itself.
        useEffect(
            (search, dialog) => {
                const target = search || dialog;
                if (target) {
                    target.focus();
                }
            },
            () => [this.searchRef.el, this.dialogRef.el]
        );

        this.state = useState({
            isOpen: false,
            searchQuery: "",
            filteredApps: [],
            searchResults: [],  // Combined results: apps + sub-menus
            appGroups: [],
            ungroupedApps: [],
            expandedGroups: {},
            loading: false,
            hasGroups: false,
            isSearchExpanded: false,  // Toggle for search bar visibility
            // Sub-menu view state
            viewMode: 'apps',  // 'apps' or 'submenus' or 'search'
            selectedApp: null,
            currentAppSections: [],
            expandedSections: {},
        });

        // Get all apps
        this.allApps = this.menuService.getApps();
        this.state.filteredApps = [...this.allApps];

        // Bind event handlers
        this._boundOnOpen = () => this.open();
        this._boundOnClose = () => this.close();
        this._boundOnToggle = () => this.toggle();
        this._boundOnKeyDown = (ev) => this._handleGlobalKeyDown(ev);

        onMounted(() => {
            // Listen for theme service events
            if (this.themeService && this.themeService.bus) {
                this.themeService.bus.addEventListener('APP_DRAWER_OPEN', this._boundOnOpen);
                this.themeService.bus.addEventListener('APP_DRAWER_CLOSE', this._boundOnClose);
                this.themeService.bus.addEventListener('APP_DRAWER_TOGGLE', this._boundOnToggle);
            }

            // Also listen for custom DOM events (fallback)
            window.addEventListener('albirru-open-app-drawer', this._boundOnOpen);

            // Global keyboard shortcut (Ctrl/Cmd + Shift + K)
            document.addEventListener('keydown', this._boundOnKeyDown);

            // Pre-load app groups
            this._loadAppGroups();
        });

        onWillUnmount(() => {
            // Cleanup event listeners
            if (this.themeService && this.themeService.bus) {
                this.themeService.bus.removeEventListener('APP_DRAWER_OPEN', this._boundOnOpen);
                this.themeService.bus.removeEventListener('APP_DRAWER_CLOSE', this._boundOnClose);
                this.themeService.bus.removeEventListener('APP_DRAWER_TOGGLE', this._boundOnToggle);
            }
            window.removeEventListener('albirru-open-app-drawer', this._boundOnOpen);
            document.removeEventListener('keydown', this._boundOnKeyDown);
        });
    }

    /**
     * Handle global keyboard shortcuts
     */
    _handleGlobalKeyDown(ev) {
        // Ctrl/Cmd + Shift + K to open drawer (Ctrl+K reserved for Search Modal)
        if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && ev.key === 'K') {
            ev.preventDefault();
            this.toggle();
        }
    }

    /**
     * Load app groups through the shared theme service cache.
     */
    async _loadAppGroups(forceRefresh = false) {
        if (!this.themeService) {
            this.state.hasGroups = false;
            return;
        }
        try {
            this.state.loading = true;
            this._applyAppGroupsData(await this.themeService.getAppGroups(forceRefresh));
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Apply app groups data to state
     */
    _applyAppGroupsData(result) {
        if (result && result.groups) {
            this.state.appGroups = result.groups;
            this.state.hasGroups = result.groups.length > 0;

            // Initialize expanded state for all groups
            result.groups.forEach(group => {
                if (this.state.expandedGroups[group.id] === undefined) {
                    this.state.expandedGroups[group.id] = true;
                }
            });
            // Also expand ungrouped section by default
            if (this.state.expandedGroups['ungrouped'] === undefined) {
                this.state.expandedGroups['ungrouped'] = true;
            }
        } else {
            this.state.hasGroups = false;
        }

        if (result && result.ungrouped_menus) {
            // Map ungrouped menus to app format
            this.state.ungroupedApps = result.ungrouped_menus.map(menu => {
                const app = this.allApps.find(a => a.id === menu.id);
                return app || menu;
            });
        }
    }

    /**
     * Toggle app drawer
     */
    toggle() {
        if (this.state.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    /**
     * Open app drawer
     */
    open() {
        this._previouslyFocused = document.activeElement;
        this.state.isOpen = true;
        this.state.searchQuery = "";
        this.state.filteredApps = [...this.allApps];
        // Reset to apps view
        this.state.viewMode = 'apps';
        this.state.selectedApp = null;
        this.state.currentAppSections = [];
        this.state.expandedSections = {};

        // Load app groups (uses cache if valid)
        this._loadAppGroups();
        // Focus is moved by the useEffect in setup(), once rendered.

        // Add body class
        document.body.classList.add("albirru-drawer-open");
    }

    /**
     * Close app drawer
     */
    close() {
        this.state.isOpen = false;
        this.state.searchQuery = "";
        this.state.viewMode = 'apps';
        this.state.selectedApp = null;
        this.state.currentAppSections = [];
        document.body.classList.remove("albirru-drawer-open");

        // Hand focus back to whatever opened the drawer.
        if (this._previouslyFocused?.isConnected) {
            this._previouslyFocused.focus();
        }
        this._previouslyFocused = null;
    }

    /**
     * Toggle search bar visibility
     */
    toggleSearch() {
        this.state.isSearchExpanded = !this.state.isSearchExpanded;
        if (this.state.isSearchExpanded) {
            this.state.viewMode = 'search';
            // Focus follows from the useEffect once the input is rendered.
        } else {
            this.closeSearch();
        }
    }

    /**
     * Close search and return to apps view
     */
    closeSearch() {
        this.state.isSearchExpanded = false;
        this.state.searchQuery = "";
        this.state.searchResults = [];
        this.state.viewMode = 'apps';
    }

    /**
     * Handle search input
     */
    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        this._filterApps();
    }

    /**
     * Filter apps AND sub-menus based on search query
     */
    _filterApps() {
        const query = this.state.searchQuery.trim().toLowerCase();

        if (!query) {
            this.state.filteredApps = [...this.allApps];
            this.state.searchResults = [];
            return;
        }

        // Search in apps
        const appNames = this.allApps.map((app) => app.name);
        const appMatches = fuzzyLookup(query, appNames, (name) => name);
        const matchedApps = this.allApps.filter((app) => appMatches.includes(app.name));

        // Search in ALL menus (including sub-menus)
        const allMenus = this._getAllMenusFlat();
        const menuResults = allMenus.filter(menu =>
            menu.name.toLowerCase().includes(query) &&
            !matchedApps.find(app => app.id === menu.id)  // Avoid duplicates
        );

        this.state.filteredApps = matchedApps;
        this.state.searchResults = [...matchedApps.map(app => ({ ...app, type: 'app' })), ...menuResults.map(menu => ({ ...menu, type: 'submenu' }))];
    }

    /**
     * Get all menus (apps + sub-menus) as flat array
     */
    _getAllMenusFlat() {
        const results = [];
        const processMenu = (menu, parentPath = '') => {
            const path = parentPath ? `${parentPath} / ${menu.name}` : menu.name;
            results.push({
                id: menu.id,
                name: menu.name,
                actionID: menu.actionID,
                actionPath: menu.actionPath,
                path: path,
                xmlid: menu.xmlid
            });
            if (menu.childrenTree) {
                menu.childrenTree.forEach(child => processMenu(child, path));
            }
        };

        this.allApps.forEach(app => {
            const menuTree = this.menuService.getMenuAsTree(app.id);
            if (menuTree && menuTree.childrenTree) {
                menuTree.childrenTree.forEach(child => processMenu(child, app.name));
            }
        });

        return results;
    }

    /**
     * Handle search result click
     */
    async onSearchResultClick(result, ev) {
        ev.preventDefault();
        this.close();
        await this.menuService.selectMenu(result);
    }

    /**
     * Get filtered apps for a specific group
     */
    getFilteredGroupApps(group) {
        if (!this.state.searchQuery) {
            return group.menus.map(menu => {
                const app = this.allApps.find(a => a.id === menu.id);
                return app || menu;
            });
        }

        const query = this.state.searchQuery.trim().toLowerCase();
        return group.menus.filter(menu =>
            menu.name.toLowerCase().includes(query)
        ).map(menu => {
            const app = this.allApps.find(a => a.id === menu.id);
            return app || menu;
        });
    }

    /**
     * Get filtered ungrouped apps
     */
    getFilteredUngroupedApps() {
        if (!this.state.searchQuery) {
            return this.state.ungroupedApps;
        }

        const query = this.state.searchQuery.trim().toLowerCase();
        return this.state.ungroupedApps.filter(app =>
            app.name.toLowerCase().includes(query)
        );
    }

    /**
     * Check if group has visible apps after filtering
     */
    groupHasVisibleApps(group) {
        return this.getFilteredGroupApps(group).length > 0;
    }

    /**
     * Toggle group expansion
     */
    toggleGroup(groupId) {
        this.state.expandedGroups[groupId] = !this.state.expandedGroups[groupId];
    }

    /**
     * Check if group is expanded
     */
    isGroupExpanded(groupId) {
        return this.state.expandedGroups[groupId] !== false;
    }

    /**
     * Check if app drawer has a background image
     */
    get hasBackgroundImage() {
        if (this.themeService) {
            const settings = this.themeService.getSettings();
            return settings.has_menu_background || false;
        }
        return false;
    }

    /**
     * Handle app click - show sub-menus if available (mobile only)
     */
    async onAppClick(app, ev) {
        ev.preventDefault();

        // Get full app from menu service
        const fullApp = this.menuService.getApps().find(a => a.id === app.id) || app;

        // Only show sub-menus on mobile view.
        // On desktop, navigate directly since sub-menus are in navbar.
        if (this.ui.isSmall) {
            // Get menu tree to check for sub-menus
            const menuTree = this.menuService.getMenuAsTree(fullApp.id);
            const sections = menuTree?.childrenTree || [];

            // If app has sub-menus, show them instead of navigating
            if (sections.length > 0) {
                this.state.viewMode = 'submenus';
                this.state.selectedApp = fullApp;
                this.state.currentAppSections = sections;
                this.state.expandedSections = {};
                return;
            }
        }

        // No sub-menus: navigate directly
        this.close();
        await this.menuService.selectMenu(fullApp);
    }

    /**
     * Go back to apps view from sub-menu view
     */
    onBackToApps() {
        this.state.viewMode = 'apps';
        this.state.selectedApp = null;
        this.state.currentAppSections = [];
        this.state.expandedSections = {};
    }

    /**
     * Handle section (sub-menu) click
     */
    async onSectionClick(section, ev) {
        ev.preventDefault();
        this.close();
        await this.menuService.selectMenu(section);
    }

    /**
     * Toggle section expansion for nested sub-menus
     */
    toggleSectionExpand(sectionId) {
        this.state.expandedSections[sectionId] = !this.state.expandedSections[sectionId];
    }

    /**
     * Check if section is expanded
     */
    isSectionExpanded(sectionId) {
        return this.state.expandedSections[sectionId] === true;
    }

    /**
     * Get menu item href for accessibility
     */
    getMenuItemHref(menu) {
        if (menu.actionPath) {
            return '/odoo/' + menu.actionPath;
        } else if (menu.actionID) {
            return '/odoo/action-' + menu.actionID;
        }
        return '#';
    }

    /**
     * Handle keyboard events in drawer
     */
    onKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
        }
    }

    /**
     * Handle backdrop click
     */
    onBackdropClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.close();
        }
    }

    /**
     * Get app icon or generate default
     */
    getAppIcon(app) {
        if (app.webIconData) {
            return app.webIconData;
        }
        return null;
    }

    /**
     * Get app initials for placeholder
     */
    getAppInitials(app) {
        return app.name
            .split(" ")
            .map((word) => word[0])
            .join("")
            .substring(0, 2)
            .toUpperCase();
    }

    /**
     * Get app background color based on name
     */
    getAppColor(app) {
        const colors = [
            "#714B67", "#2e7d32", "#5e35b1", "#ef6c00",
            "#c62828", "#00796b", "#1565c0", "#6a1b9a"
        ];
        const hash = app.name.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return colors[hash % colors.length];
    }

    /**
     * Get group icon URL
     */
    getGroupIconUrl(group) {
        if (group.has_group_icon) {
            return `/web/image/albirru.app.group/${group.id}/group_menu_icon`;
        }
        return null;
    }

    /**
     * Get total visible apps count
     */
    getTotalVisibleApps() {
        if (this.state.searchQuery) {
            return this.state.filteredApps.length;
        }
        return this.allApps.length;
    }
}

// Register as main component
if (session.albirru_theme_installed) {
    registry.category("main_components").add("AlbirruAppDrawer", {
        Component: AlbirruAppDrawer,
        props: {},
    }, { sequence: 99 });
}
