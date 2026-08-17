/** @odoo-module **/
// Albirru Backend Theme - Fullscreen Toggle Component
// Compatible with Odoo 19

import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

/**
 * Fullscreen Toggle Component for Systray
 * Provides fullscreen toggle functionality in the systray area
 */
export class AlbirruFullscreenToggle extends Component {
    static template = "albirru_backend_theme.FullscreenToggle";
    static props = {};

    setup() {
        this.state = useState({
            isFullscreen: this._checkFullscreen(),
        });

        // Bind handler for proper cleanup
        this._boundOnFullscreenChange = () => {
            this.state.isFullscreen = this._checkFullscreen();
        };

        // Listen for fullscreen change
        document.addEventListener("fullscreenchange", this._boundOnFullscreenChange);

        // Cleanup on unmount to prevent memory leaks
        onWillUnmount(() => {
            document.removeEventListener("fullscreenchange", this._boundOnFullscreenChange);
        });
    }

    /**
     * Check if currently in fullscreen
     */
    _checkFullscreen() {
        return !!(
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            document.mozFullScreenElement ||
            document.msFullscreenElement
        );
    }

    /**
     * Toggle fullscreen mode
     */
    async onToggle() {
        try {
            if (this.state.isFullscreen) {
                // Exit fullscreen
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    await document.webkitExitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    await document.mozCancelFullScreen();
                } else if (document.msExitFullscreen) {
                    await document.msExitFullscreen();
                }
            } else {
                // Enter fullscreen
                const elem = document.documentElement;
                if (elem.requestFullscreen) {
                    await elem.requestFullscreen();
                } else if (elem.webkitRequestFullscreen) {
                    await elem.webkitRequestFullscreen();
                } else if (elem.mozRequestFullScreen) {
                    await elem.mozRequestFullScreen();
                } else if (elem.msRequestFullscreen) {
                    await elem.msRequestFullscreen();
                }
            }
        } catch (error) {
            console.error("Fullscreen toggle failed:", error);
        }
    }

    /**
     * Get icon class
     */
    get iconClass() {
        return this.state.isFullscreen ? "fa-compress" : "fa-expand";
    }

    /**
     * Get tooltip text
     */
    get tooltipText() {
        return this.state.isFullscreen ? _t("Exit Fullscreen") : _t("Enter Fullscreen");
    }
}

// Register in systray - Odoo 19 uses simple { Component } format
if (session.albirru_theme_installed) {
    registry.category("systray").add("albirru.FullscreenToggle", {
        Component: AlbirruFullscreenToggle,
    }, { sequence: 8 });
}
