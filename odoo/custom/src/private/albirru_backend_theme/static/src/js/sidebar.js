/** @odoo-module **/
// Albirru Backend Theme - Sidebar Component
// Compatible with Odoo 19

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

/**
 * Albirru Sidebar Component
 * A collapsible left sidebar menu for Odoo backend
 * Now displays App Groups and Apps as the primary navigation
 */
export class AlbirruSidebar extends Component {
    static template = "albirru_backend_theme.Sidebar";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.albirruTheme = useService("albirruTheme");
        this.ui = useService("ui");

        this.sidebarRef = useRef("sidebar");

        this.state = useState({
            isPinned: this.albirruTheme.isSidebarPinned(),
            position: this.albirruTheme.getSettings().sidebar_position || 'left',
            isHovered: false,
            expandedGroups: new Set(),
            expandedSections: new Set(),
            currentAppId: null,
            currentAppSections: [],
            appGroups: [],
            ungroupedApps: [],
            loading: true,
            isMobileOpen: false,
        });

        // Bind handlers once for proper cleanup
        this._boundOnAppChanged = this._onAppChanged.bind(this);
        this._boundOnThemeChanged = this._onThemeChanged.bind(this);
        this._boundOnMobileToggle = this._onMobileToggle.bind(this);

        // Listen for menu changes
        this.env.bus.addEventListener("MENUS:APP-CHANGED", this._boundOnAppChanged);

        // Listen for theme changes
        this.albirruTheme.bus.addEventListener('THEME_CHANGED', this._boundOnThemeChanged);

        // Listen for mobile sidebar toggle from navbar hamburger
        this.env.bus.addEventListener("ALBIRRU:TOGGLE-MOBILE-SIDEBAR", this._boundOnMobileToggle);

        onMounted(() => {
            this._initSidebar();
            this._loadAppGroups();
        });

        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", this._boundOnAppChanged);
            this.albirruTheme.bus.removeEventListener('THEME_CHANGED', this._boundOnThemeChanged);
            this.env.bus.removeEventListener("ALBIRRU:TOGGLE-MOBILE-SIDEBAR", this._boundOnMobileToggle);
        });
    }

    /**
     * Initialize sidebar
     */
    _initSidebar() {
        const currentApp = this.menuService.getCurrentApp();
        if (currentApp) {
            this.state.currentAppId = currentApp.id;
            this._updateCurrentAppSections();
        }
    }

    /**
     * Load app groups from backend
     */
    async _loadAppGroups() {
        try {
            this.state.loading = true;
            const result = await this.albirruTheme.getAppGroups();

            if (result) {
                this.state.appGroups = result.groups || [];
                // Map ungrouped menus to full app objects from menu service
                const allApps = this.menuService.getApps();
                this.state.ungroupedApps = (result.ungrouped_menus || []).map(m => {
                    const app = allApps.find(a => a.id === m.id);
                    return app || m;
                });

                // Expand groups that contain the active app
                this._expandActiveGroup();
            }
        } catch (error) {
            console.error('[AlbirruSidebar] Failed to load app groups:', error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Expand group containing the active app
     */
    _expandActiveGroup() {
        const appId = this.state.currentAppId;
        if (!appId) return;

        for (const group of this.state.appGroups) {
            if (group.menus.some(m => m.id === appId)) {
                this.state.expandedGroups.add(group.id);
                break;
            }
        }
        // Force reactivity
        this.state.expandedGroups = new Set(this.state.expandedGroups);
    }

    /**
     * Handle app change
     */
    _onAppChanged() {
        const currentApp = this.menuService.getCurrentApp();
        if (currentApp) {
            if (this.state.currentAppId !== currentApp.id) {
                this.state.currentAppId = currentApp.id;
                this._expandActiveGroup();
                // Update current app sections
                this._updateCurrentAppSections();
            }
        }
    }

    /**
     * Update current app sections (sub-menus)
     */
    _updateCurrentAppSections() {
        const app = this.menuService.getCurrentApp();
        if (app) {
            const menuTree = this.menuService.getMenuAsTree(app.id);
            this.state.currentAppSections = menuTree?.childrenTree || [];
        } else {
            this.state.currentAppSections = [];
        }
        // Reset expanded sections when app changes
        this.state.expandedSections = new Set();
    }

    /**
     * Handle theme change
     */
    _onThemeChanged(ev) {
        if (ev.detail.setting === 'sidebar_pinned') {
            this.state.isPinned = ev.detail.value;
        } else if (ev.detail.setting === 'sidebar_position') {
            this.state.position = ev.detail.value;
        }
    }

    /**
     * The sidebar only exists in the "left" menu layout; in "top" layout the
     * navbar carries the menus instead.
     */
    get isVisible() {
        return this.state.position === 'left';
    }

    /**
     * Get current app
     */
    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    /**
     * Get branding info
     */
    get branding() {
        return this.albirruTheme.getBranding();
    }

    /**
     * Get session data for company ID
     */
    get session() {
        return session;
    }

    /**
     * Tooltip for the pin button.
     *
     * Lives here rather than inline in the template because QWeb only extracts
     * literal attribute values for translation, not expressions.
     */
    get pinTooltip() {
        return this.state.isPinned ? _t("Unpin Sidebar") : _t("Pin Sidebar");
    }

    /**
     * Check if sidebar is collapsed (not pinned and not hovered)
     */
    get isCollapsed() {
        return !this.state.isPinned && !this.state.isHovered;
    }

    /**
     * Check if sidebar has a background image
     */
    get hasBackgroundImage() {
        const settings = this.albirruTheme.getSettings();
        return settings.has_menu_background || false;
    }

    /**
     * Toggle group expansion
     */
    toggleGroup(groupId) {
        if (this.state.expandedGroups.has(groupId)) {
            this.state.expandedGroups.delete(groupId);
        } else {
            this.state.expandedGroups.add(groupId);
        }
        // Force reactivity
        this.state.expandedGroups = new Set(this.state.expandedGroups);
    }

    /**
     * Check if group is expanded
     */
    isGroupExpanded(groupId) {
        return this.state.expandedGroups.has(groupId);
    }

    /**
     * Check if app is active
     */
    isAppActive(appId) {
        return this.state.currentAppId === appId;
    }

    /**
     * Check if we're in mobile mode.
     *
     * Uses the ui service rather than reading window.innerWidth directly, so
     * the value stays correct after a resize or a device rotation.
     */
    isMobile() {
        return this.ui.isSmall;
    }

    /**
     * Handle app click
     * On mobile: show sub-menus first, don't navigate immediately
     * On desktop: navigate immediately
     */
    async onAppClick(app, ev) {
        ev.preventDefault();

        // The app from app_groups controller might be a simplified object
        // Get the full app object from menuService if possible
        const fullApp = this.menuService.getApps().find(a => a.id === app.id) || app;

        // On mobile, show sub-menus instead of immediately navigating
        if (this.isMobile() && this.state.isMobileOpen) {
            // Get the menu tree for this app
            const menuTree = this.menuService.getMenuAsTree(fullApp.id);
            const sections = menuTree?.childrenTree || [];

            // If app has sub-menus, show them instead of navigating
            if (sections.length > 0) {
                this.state.currentAppId = fullApp.id;
                this.state.currentAppSections = sections;
                this.state.expandedSections = new Set();
                // DON'T close sidebar - keep it open to show sub-menus
                return;
            }
        }

        // No sub-menus or desktop mode: navigate directly
        this.state.isMobileOpen = false;
        await this.menuService.selectMenu(fullApp);
        // Update sections after app change
        this._updateCurrentAppSections();
    }

    /**
     * Toggle section expansion (for sub-menus with children)
     */
    toggleSection(sectionId) {
        if (this.state.expandedSections.has(sectionId)) {
            this.state.expandedSections.delete(sectionId);
        } else {
            this.state.expandedSections.add(sectionId);
        }
        // Force reactivity
        this.state.expandedSections = new Set(this.state.expandedSections);
    }

    /**
     * Check if section is expanded
     */
    isSectionExpanded(sectionId) {
        return this.state.expandedSections.has(sectionId);
    }

    /**
     * Handle section click (navigate to menu)
     */
    async onSectionClick(section, ev) {
        ev.preventDefault();
        // Close mobile sidebar after section selection
        this.state.isMobileOpen = false;
        await this.menuService.selectMenu(section);
    }

    /**
     * Get menu item href
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
     * Handle mobile sidebar toggle event
     */
    _onMobileToggle() {
        this.state.isMobileOpen = !this.state.isMobileOpen;
    }

    /**
     * Close mobile sidebar
     */
    closeMobileSidebar() {
        this.state.isMobileOpen = false;
    }

    /**
     * Handle backdrop click on mobile
     */
    onBackdropClick() {
        this.state.isMobileOpen = false;
    }

    /**
     * Handle mouse enter
     */
    onMouseEnter() {
        this.state.isHovered = true;
    }

    /**
     * Handle mouse leave
     */
    onMouseLeave() {
        this.state.isHovered = false;
    }

    /**
     * Toggle pin state
     */
    async onTogglePin() {
        await this.albirruTheme.toggleSidebarPinned();
    }

    /**
     * Get app icon data
     */
    getAppIcon(app) {
        if (app.webIconData) return app.webIconData;

        // Find in menu service apps
        const menuApp = this.menuService.getApps().find(a => a.id === app.id);
        if (menuApp && menuApp.webIconData) return menuApp.webIconData;

        return null;
    }

    /**
     * Get app initials for placeholder
     */
    getAppInitials(app) {
        if (!app || !app.name) return '';
        return app.name
            .split(' ')
            .map((word) => word[0])
            .join('')
            .substring(0, 2)
            .toUpperCase();
    }

    /**
     * Get app background color based on name
     */
    getAppColor(app) {
        if (!app || !app.name) return '#714B67';
        const colors = [
            '#714B67', '#2e7d32', '#5e35b1', '#ef6c00',
            '#c62828', '#00796b', '#1565c0', '#6a1b9a'
        ];
        const hash = app.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
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
}

// Register sidebar component in main components registry.
// Always registered: the component renders nothing when the menu is set to the
// top position, so switching position no longer requires a page reload.
if (session.albirru_theme_installed) {
    registry.category("main_components").add("AlbirruSidebar", {
        Component: AlbirruSidebar,
        props: {},
    }, { sequence: 5 });
}
