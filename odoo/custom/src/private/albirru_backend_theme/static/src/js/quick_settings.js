/** @odoo-module **/
// Albirru Backend Theme - Quick Settings Component
// Compatible with Odoo 19

import { Component, useState, useRef, onWillPatch, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

// Static data for options
const COLOR_SCHEMES = [
    { id: "scheme_1", name: _t("Odoo Purple"), color: "#714B67" },
    { id: "scheme_2", name: _t("Green"), color: "#2e7d32" },
    { id: "scheme_3", name: _t("Purple"), color: "#5e35b1" },
    { id: "scheme_4", name: _t("Orange"), color: "#ef6c00" },
    { id: "scheme_5", name: _t("Red"), color: "#c62828" },
    { id: "scheme_6", name: _t("Teal"), color: "#00796b" },
    { id: "scheme_7", name: _t("Pink"), color: "#d81b60" },
    { id: "scheme_8", name: _t("Blue"), color: "#1565c0" },
    { id: "scheme_9", name: _t("Indigo"), color: "#303f9f" },
    { id: "scheme_10", name: _t("Amber"), color: "#ff8f00" },
    { id: "scheme_11", name: _t("Cyan"), color: "#0097a7" },
    { id: "scheme_12", name: _t("Brown"), color: "#5d4037" },
    { id: "scheme_13", name: _t("Black"), color: "#212121" },
    { id: "scheme_14", name: _t("Lime"), color: "#689f38" },
    { id: "scheme_15", name: _t("Deep Purple"), color: "#4527a0" },
    { id: "scheme_16", name: _t("Light Blue"), color: "#0288d1" },
    { id: "scheme_17", name: _t("Grey"), color: "#616161" },
    { id: "scheme_18", name: _t("Blue Grey"), color: "#455a64" },
];

const THEME_STYLES = [
    { id: "rounded", name: _t("Rounded"), icon: "fa-circle-o" },
    { id: "standard", name: _t("Standard"), icon: "fa-square-o" },
    { id: "square", name: _t("Square"), icon: "fa-stop" },
];

const SIDEBAR_POSITIONS = [
    { id: "left", name: _t("Left Sidebar"), icon: "fa-columns" },
    { id: "top", name: _t("Top Menu"), icon: "fa-bars" },
];



const FONT_FAMILIES = [
    { id: "inter", name: "Inter" },
    { id: "roboto", name: "Roboto" },
    { id: "poppins", name: "Poppins" },
    { id: "open_sans", name: "Open Sans" },
    { id: "lato", name: "Lato" },
    { id: "nunito", name: "Nunito" },
];

const FONT_SIZES = [
    { id: "small", name: _t("Small") },
    { id: "medium", name: _t("Medium") },
    { id: "large", name: _t("Large") },
];

const CHATTER_POSITIONS = [
    { id: "right", name: _t("Right"), icon: "fa-align-right" },
    { id: "bottom", name: _t("Bottom"), icon: "fa-align-justify" },
];

const LIST_ROW_HEIGHTS = [
    { id: "compact", name: _t("Compact") },
    { id: "comfortable", name: _t("Comfortable") },
];

const BUTTON_STYLES = [
    { id: "filled", name: _t("Filled") },
    { id: "outlined", name: _t("Outlined") },
    { id: "soft", name: _t("Soft") },
];

const INPUT_STYLES = [
    { id: "bordered", name: _t("Bordered") },
    { id: "underlined", name: _t("Underlined") },
    { id: "filled", name: _t("Filled") },
];

const LOADER_STYLES = [
    { id: "spinner", name: _t("Spinner") },
    { id: "dots", name: _t("Dots") },
    { id: "bar", name: _t("Progress Bar") },
];

/**
 * Quick Settings Panel Component for Systray
 */
export class AlbirruQuickSettings extends Component {
    static template = "albirru_backend_theme.QuickSettings";
    static props = {};

    setup() {
        this.albirruTheme = useService("albirruTheme");
        this.actionService = useService("action");
        this.bodyRef = useRef("settingsBody");
        this.fileInputRef = useRef("fileInput");

        const settings = this.albirruTheme.getSettings();

        this.state = useState({
            isOpen: false,
            activeTab: "appearance",
            isDarkMode: settings.dark_mode || false,
            colorScheme: settings.color_scheme || "scheme_1",
            themeStyle: settings.theme_style || "rounded",
            sidebarPosition: settings.sidebar_position || "left",
            fontFamily: settings.font_family || "inter",
            fontSize: settings.font_size || "medium",
            chatterPosition: settings.chatter_position || "right",
            sidebarPinned: settings.sidebar_pinned !== false,

            useCustomColors: settings.use_custom_colors || false,
            primaryColor: settings.primary_color || "#714B67",
            secondaryColor: settings.secondary_color || "#ffffff",
            accentColor: settings.accent_color || "#017e84",
            listRowHeight: settings.list_row_height || "comfortable",
            listStickyHeader: settings.list_sticky_header !== false,
            buttonStyle: settings.button_style || "filled",
            inputStyle: settings.input_style || "bordered",
            loaderStyle: settings.loader_style || "spinner",
            hasMenuBackground: settings.has_menu_background || false,
            menuBgOpacity: settings.menu_bg_opacity || 15,
            overridden: this.albirruTheme.getOverriddenKeys(),
        });

        // Company-wide controls (shared menu background) stay admin-only.
        this.isAdmin = !!session.albirru_is_admin;

        // The company may have reserved the theme for itself. Employees do not
        // get this panel at all then (it is not registered in the systray);
        // administrators keep it, but every change they make applies to the
        // whole company rather than to themselves.
        this.isLocked = this.albirruTheme.isThemeLocked();

        // Preserve scroll position on updates
        onWillPatch(() => {
            if (this.bodyRef.el) {
                this.scrollPosition = this.bodyRef.el.scrollTop;
            }
        });

        onPatched(() => {
            if (this.bodyRef.el && this.scrollPosition) {
                this.bodyRef.el.scrollTop = this.scrollPosition;
            }
        });

        // Listen for theme changes
        this.albirruTheme.bus.addEventListener("THEME_CHANGED", (ev) => {
            if (ev.detail.setting === "dark_mode") {
                this.state.isDarkMode = ev.detail.value;
            } else if (ev.detail.setting === "sidebar_pinned") {
                this.state.sidebarPinned = ev.detail.value;
            } else if (ev.detail.setting === "primary_color") {
                this.state.primaryColor = ev.detail.value;
            } else if (ev.detail.setting === "secondary_color") {
                this.state.secondaryColor = ev.detail.value;
            } else if (ev.detail.setting === "accent_color") {
                this.state.accentColor = ev.detail.value;
            } else if (ev.detail.setting === "use_custom_colors") {
                this.state.useCustomColors = ev.detail.value;
            }
            // Any change may have created a new personal override.
            this.state.overridden = this.albirruTheme.getOverriddenKeys();
        });
    }

    /**
     * Where a change made in this panel is stored. Locked means there is no
     * personal layer left, so an administrator edits the company theme.
     */
    get saveScope() {
        return this.isLocked ? "company" : "user";
    }

    /**
     * Persist one setting at the scope this panel currently writes to.
     */
    async _save(field, value) {
        return this.albirruTheme.updateSetting(field, value, this.saveScope);
    }

    // Getters for template access
    get colorSchemes() {
        return COLOR_SCHEMES;
    }

    get themeStyles() {
        return THEME_STYLES;
    }

    get sidebarPositions() {
        return SIDEBAR_POSITIONS;
    }



    get fontFamilies() {
        return FONT_FAMILIES;
    }

    get fontSizes() {
        return FONT_SIZES;
    }

    get chatterPositions() {
        return CHATTER_POSITIONS;
    }

    get listRowHeights() {
        return LIST_ROW_HEIGHTS;
    }

    get buttonStyles() {
        return BUTTON_STYLES;
    }

    get inputStyles() {
        return INPUT_STYLES;
    }

    get loaderStyles() {
        return LOADER_STYLES;
    }

    /**
     * Set active tab
     */
    setActiveTab(tab) {
        this.state.activeTab = tab;
    }

    /**
     * Toggle dark mode - with event handling to prevent dropdown jump
     */
    async onToggleDarkMode(ev) {
        // Prevent event from bubbling up and causing dropdown issues
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }

        // Store current dropdown state
        const dropdown = document.querySelector('.albirru-settings-dropdown');
        const scrollPosition = this.bodyRef.el ? this.bodyRef.el.scrollTop : 0;

        // Toggle dark mode
        await this.albirruTheme.toggleDarkMode();

        // Restore scroll position after render
        requestAnimationFrame(() => {
            if (this.bodyRef.el) {
                this.bodyRef.el.scrollTop = scrollPosition;
            }
        });
    }

    /**
     * Toggle sidebar pinned
     */
    async onToggleSidebarPinned() {
        await this.albirruTheme.toggleSidebarPinned();
    }

    /**
     * Select color scheme
     */
    async onSelectColorScheme(schemeId) {
        this.state.colorScheme = schemeId;
        await this._save("color_scheme", schemeId);
    }

    /**
     * Select theme style
     */
    async onSelectThemeStyle(styleId) {
        this.state.themeStyle = styleId;
        await this._save("theme_style", styleId);
    }

    /**
     * Select sidebar position. Applied live - no reload needed since the
     * sidebar component is always mounted and hides itself when unused.
     */
    async onSelectSidebarPosition(positionId) {
        this.state.sidebarPosition = positionId;
        await this._save("sidebar_position", positionId);
        this._syncOverridden();
    }

    /**
     * Refresh the "personalised" markers after a change.
     */
    _syncOverridden() {
        this.state.overridden = this.albirruTheme.getOverriddenKeys();
    }

    /**
     * Whether this setting differs from the company default.
     */
    isOverridden(field) {
        return this.state.overridden.includes(field);
    }

    get hasOverrides() {
        return this.state.overridden.length > 0;
    }

    /**
     * Discard every personal override and fall back to the company theme.
     */
    async onResetToCompanyDefaults() {
        const result = await this.albirruTheme.resetSetting();
        if (!result?.success) {
            return;
        }
        const settings = result.settings || {};
        Object.assign(this.state, {
            colorScheme: settings.color_scheme,
            themeStyle: settings.theme_style,
            sidebarPosition: settings.sidebar_position,
            fontFamily: settings.font_family,
            fontSize: settings.font_size,
            chatterPosition: settings.chatter_position,
            useCustomColors: settings.use_custom_colors,
            primaryColor: settings.primary_color,
            secondaryColor: settings.secondary_color,
            accentColor: settings.accent_color,
            listRowHeight: settings.list_row_height,
            listStickyHeader: settings.list_sticky_header,
            buttonStyle: settings.button_style,
            inputStyle: settings.input_style,
            loaderStyle: settings.loader_style,
            overridden: [],
        });
    }



    /**
     * Toggle use custom colors
     */
    async onToggleCustomColors() {
        const newValue = !this.state.useCustomColors;
        this.state.useCustomColors = newValue;
        await this._save("use_custom_colors", newValue);
    }

    /**
     * Update custom color
     */
    async onUpdateCustomColor(field, value) {
        this.state[field] = value;
        // Convert camelCase to snake_case for backend
        const fieldMap = {
            'primaryColor': 'primary_color',
            'secondaryColor': 'secondary_color',
            'accentColor': 'accent_color'
        };
        const backendField = fieldMap[field] || field;
        await this._save(backendField, value);
    }

    /**
     * Select font family
     */
    async onSelectFontFamily(fontId) {
        this.state.fontFamily = fontId;
        await this._save("font_family", fontId);
    }

    /**
     * Select font size
     */
    async onSelectFontSize(sizeId) {
        this.state.fontSize = sizeId;
        await this._save("font_size", sizeId);
    }

    /**
     * Select chatter position
     */
    async onSelectChatterPosition(positionId) {
        this.state.chatterPosition = positionId;
        await this._save("chatter_position", positionId);
    }

    /**
     * Select list row height
     */
    async onSelectListRowHeight(heightId) {
        this.state.listRowHeight = heightId;
        await this._save("list_row_height", heightId);
    }

    /**
     * Toggle sticky list header
     */
    async onToggleStickyHeader() {
        const newValue = !this.state.listStickyHeader;
        this.state.listStickyHeader = newValue;
        await this._save("list_sticky_header", newValue);
    }

    /**
     * Select button style
     */
    async onSelectButtonStyle(styleId) {
        this.state.buttonStyle = styleId;
        await this._save("button_style", styleId);
    }

    /**
     * Select input style
     */
    async onSelectInputStyle(styleId) {
        this.state.inputStyle = styleId;
        await this._save("input_style", styleId);
    }

    /**
     * Select loader style
     */
    async onSelectLoaderStyle(styleId) {
        this.state.loaderStyle = styleId;
        await this._save("loader_style", styleId);
    }

    /**
     * Change menu background opacity
     */
    async onMenuBgOpacityChange(ev) {
        const opacity = parseInt(ev.target.value, 10);
        this.state.menuBgOpacity = opacity;
        // Apply opacity immediately via CSS variable
        document.documentElement.style.setProperty('--albirru-menu-bg-opacity', opacity / 100);
        // Save to backend
        await this.albirruTheme.updateSetting("menu_bg_opacity", opacity, "company");
    }

    /**
     * Upload menu background image
     */
    async onUploadMenuBackground(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const base64 = e.target.result.split(',')[1];
                await this.albirruTheme.updateSetting("menu_background", base64, "company");
                this.state.hasMenuBackground = true;
                this._refreshBackground();
            } catch (error) {
                console.error("Failed to upload background", error);
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Remove menu background image
     */
    async onRemoveMenuBackground() {
        try {
            await this.albirruTheme.updateSetting("menu_background", false, "company");
            this.state.hasMenuBackground = false;
            // Clear file input
            if (this.fileInputRef.el) {
                this.fileInputRef.el.value = '';
            }
            this._refreshBackground();
        } catch (error) {
            console.error("Failed to remove background", error);
        }
    }

    /**
     * Refresh background CSS and cache
     */
    _refreshBackground() {
        if (this.state.hasMenuBackground) {
            const unique = new Date().getTime();
            const url = `/albirru_backend_theme/menu_background?unique=${unique}`;
            document.documentElement.style.setProperty('--albirru-menu-bg-image', `url('${url}')`);
            document.documentElement.setAttribute('data-albirru-menu-bg', 'true');
            // Re-apply opacity
            const opacity = (this.state.menuBgOpacity || 15) / 100;
            document.documentElement.style.setProperty('--albirru-menu-bg-opacity', opacity);
        } else {
            document.documentElement.style.removeProperty('--albirru-menu-bg-image');
            document.documentElement.style.removeProperty('--albirru-menu-bg-opacity');
            document.documentElement.removeAttribute('data-albirru-menu-bg');
        }
    }

    /**
     * Open full settings without reloading the page
     */
    async onOpenFullSettings() {
        this.state.isOpen = false;
        await this.actionService.doAction("base_setup.action_general_configuration");
    }
}

// Register in systray - Odoo 19 uses simple { Component } format.
//
// The panel edits personal preferences layered on top of the company defaults,
// so every user gets it - except when the company runs a single locked theme,
// where an employee has nothing left to change. Dark mode is not lost with it:
// it has its own systray toggle (see dark_mode_toggle.js).
const canOpenQuickSettings =
    !session.albirru_theme_locked || !!session.albirru_is_admin;

if (session.albirru_theme_installed && canOpenQuickSettings) {
    registry.category("systray").add("albirru.QuickSettings", {
        Component: AlbirruQuickSettings,
    }, { sequence: 4 });
}
