/** @odoo-module **/
import { menuService } from "@web/webclient/menus/menu_service";
import { patch } from "@web/core/utils/patch";

patch(menuService, {
    async start(env) {
        const result = await super.start(...arguments);
        let currentMenu = null;

        const originalSetCurrentMenu = result.setCurrentMenu;
        result.setCurrentMenu = (menu) => {
            const menuObj = typeof menu === "number" ? result.getMenu(menu) : menu;
            const menuChanged = !currentMenu || !menuObj || currentMenu.id !== menuObj.id;
            
            // Get current app ID before it might be changed
            const currentApp = result.getCurrentApp();
            const currentAppId = currentApp ? currentApp.id : null;
            const appChanged = menuObj && menuObj.appID !== currentAppId;
            
            currentMenu = menuObj;
            originalSetCurrentMenu(menu);
            
            if (menuChanged && !appChanged) {
                // If app changed, originalSetCurrentMenu already triggered MENUS:APP-CHANGED
                // If only menu changed, we trigger it manually to refresh components like sidebar
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        };

        result.getCurrentMenu = () => {
            return currentMenu;
        };

        return result;
    }
});
