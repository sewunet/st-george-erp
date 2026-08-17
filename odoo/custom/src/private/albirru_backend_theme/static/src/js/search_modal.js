/** @odoo-module **/
// Albirru Backend Theme - Global Search Modal
// Compatible with Odoo 19

import { Component, useState, useRef, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { fuzzyLookup } from "@web/core/utils/search";
import { useDebounced } from "@web/core/utils/timing";
import { KeepLast } from "@web/core/utils/concurrency";

// Wait this long after the last keystroke before querying the server.
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Global Search Modal Component
 */
export class AlbirruSearchModal extends Component {
    static template = "albirru_backend_theme.SearchModal";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");

        this.inputRef = useRef("searchInput");
        this.dialogRef = useRef("dialog");

        // Move focus into the dialog as soon as it is in the DOM, and hand it
        // back to whatever was focused before when it closes. Driven by the
        // render cycle rather than a setTimeout guess.
        useEffect(
            (input) => {
                if (input) {
                    input.focus();
                }
            },
            () => [this.inputRef.el]
        );

        this.state = useState({
            isOpen: false,
            query: "",
            searchType: "menu", // "menu" or "records"
            results: [],
            selectedIndex: 0,
            isLoading: false,
            selectedModel: "all",
            availableModels: [],
        });

        // Build searchable menus
        this._searchableMenus = this._buildSearchableMenus();

        // Discards the results of superseded requests, so a slow early query
        // can never overwrite the results of a later one.
        this.keepLast = new KeepLast();
        // useDebounced (not debounce) so a pending timer is cancelled if the
        // component ever goes away.
        this._debouncedRecordSearch = useDebounced(
            () => this._searchRecords(this.state.query.trim()),
            SEARCH_DEBOUNCE_MS
        );

        // The model list is only needed by the "Records" tab; it is fetched the
        // first time that tab is opened rather than on every page load.
        this._modelsLoaded = false;

        // Register hotkey (Ctrl+K) - Note: meta key is not supported in Odoo 19
        useHotkey("control+k", () => this.open(), { global: true });

        // Listen for custom event from systray button
        useExternalListener(window, "albirru-open-search-modal", () => this.open());
    }

    /**
     * Build searchable menus from menu service
     */
    _buildSearchableMenus() {
        const menus = {};

        for (const app of this.menuService.getApps()) {
            const tree = this.menuService.getMenuAsTree(app.id);
            this._flattenMenuTree(tree, "", menus);
        }

        return menus;
    }

    /**
     * Flatten menu tree for searching
     */
    _flattenMenuTree(menu, prefix, result) {
        if (!menu) return;

        const fullName = prefix ? `${prefix} / ${menu.name}` : menu.name;

        if (menu.actionID) {
            result[fullName] = {
                id: menu.id,
                name: fullName,
                actionID: menu.actionID,
                actionPath: menu.actionPath,
            };
        }

        if (menu.childrenTree) {
            for (const child of menu.childrenTree) {
                this._flattenMenuTree(child, fullName, result);
            }
        }
    }

    /**
     * Load the models offered in the selector. Runs at most once.
     */
    async _loadAvailableModels() {
        if (this._modelsLoaded) {
            return;
        }
        this._modelsLoaded = true;
        try {
            this.state.availableModels =
                (await rpc("/albirru_backend_theme/searchable_models", {})) || [];
        } catch (error) {
            // Silently fail - record search is an optional feature. Allow a
            // later attempt to retry.
            this._modelsLoaded = false;
            this.state.availableModels = [];
        }
    }

    /**
     * Open search modal
     */
    open() {
        // Remember where focus came from so it can be restored on close.
        this._previouslyFocused = document.activeElement;
        this.state.isOpen = true;
        this.state.query = "";
        this.state.results = [];
        this.state.selectedIndex = 0;
        // Focus is moved by the useEffect above, once the input is rendered.
    }

    /**
     * Close search modal
     */
    close() {
        this.state.isOpen = false;
        this.state.query = "";
        this.state.results = [];

        // Return focus to the element that opened the dialog, so keyboard users
        // do not get dropped back at the top of the document.
        if (this._previouslyFocused?.isConnected) {
            this._previouslyFocused.focus();
        }
        this._previouslyFocused = null;
    }

    /**
     * Keep Tab navigation inside the dialog while it is open.
     */
    _trapFocus(ev) {
        const focusables = this.dialogRef.el?.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (!focusables?.length) {
            return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (ev.shiftKey && document.activeElement === first) {
            ev.preventDefault();
            last.focus();
        } else if (!ev.shiftKey && document.activeElement === last) {
            ev.preventDefault();
            first.focus();
        }
    }

    /**
     * Handle input change
     */
    onInputChange(ev) {
        this.state.query = ev.target.value;
        this.state.selectedIndex = 0;
        this._performSearch();
    }

    /**
     * Perform search based on type.
     *
     * Menu search runs against an in-memory index, so it stays instant. Record
     * search hits the server and is therefore debounced.
     */
    _performSearch() {
        const query = this.state.query.trim();

        if (!query) {
            this.state.results = [];
            this.state.isLoading = false;
            return;
        }

        if (this.state.searchType === "menu") {
            this._searchMenus(query);
        } else {
            this.state.isLoading = true;
            this._debouncedRecordSearch();
        }
    }

    /**
     * Search menus
     */
    _searchMenus(query) {
        const menuNames = Object.keys(this._searchableMenus);
        const matches = fuzzyLookup(query, menuNames, (name) => name);

        this.state.results = matches.slice(0, 10).map((name) => ({
            type: "menu",
            ...this._searchableMenus[name],
        }));
    }

    /**
     * Search records through the single server-side endpoint.
     *
     * Superseded requests are dropped by KeepLast, so out-of-order responses
     * can never overwrite fresher results.
     */
    async _searchRecords(query) {
        if (!query) {
            this.state.isLoading = false;
            return;
        }

        try {
            const records = await this.keepLast.add(
                rpc("/albirru_backend_theme/search_records", {
                    query: query,
                    model: this.state.selectedModel,
                    limit: 15,
                })
            );
            this.state.results = (records || []).map((record) => ({
                type: "record",
                id: record.id,
                name: record.name,
                model: record.model,
                modelName: record.model_name,
            }));
        } catch (error) {
            // Silently fail - show empty results
            this.state.results = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Handle keyboard navigation
     */
    onKeyDown(ev) {
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.state.selectedIndex = Math.min(
                    this.state.selectedIndex + 1,
                    this.state.results.length - 1
                );
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.state.selectedIndex = Math.max(this.state.selectedIndex - 1, 0);
                break;
            case "Enter":
                ev.preventDefault();
                this.selectResult(this.state.results[this.state.selectedIndex]);
                break;
            case "Escape":
                this.close();
                break;
            case "Tab":
                this._trapFocus(ev);
                break;
        }
    }

    /**
     * Select a search result
     */
    async selectResult(result) {
        if (!result) return;

        this.close();

        // Navigate in-app: a full page reload would discard the whole JS bundle
        // and the current breadcrumb stack.
        if (result.type === "menu") {
            await this.menuService.selectMenu(result.id);
        } else if (result.type === "record") {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: result.model,
                res_id: result.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    /**
     * Change search type
     */
    async onSearchTypeChange(type) {
        this.state.searchType = type;
        this.state.results = [];
        this.state.selectedIndex = 0;

        if (type === "records") {
            await this._loadAvailableModels();
        }

        this._performSearch();
    }

    /**
     * Change selected model
     */
    onModelChange(ev) {
        this.state.selectedModel = ev.target.value;
        this._performSearch();
    }

    /**
     * Handle backdrop click
     */
    onBackdropClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.close();
        }
    }
}

/**
 * Systray Search Item Component
 */
export class AlbirruSearchSystray extends Component {
    static template = "albirru_backend_theme.SearchSystrayItem";
    static props = {};

    onClick() {
        const event = new CustomEvent("albirru-open-search-modal");
        window.dispatchEvent(event);
    }
}

// Register components
if (session.albirru_theme_installed) {
    registry.category("main_components").add("AlbirruSearchModal", {
        Component: AlbirruSearchModal,
        props: {},
    }, { sequence: 100 });

    registry.category("systray").add("AlbirruSearchSystray", {
        Component: AlbirruSearchSystray,
    }, { sequence: 5 }); // Low sequence to appear on the left side of systray
}
