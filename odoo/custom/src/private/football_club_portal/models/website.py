from odoo import api, models


class Website(models.Model):
    _inherit = "website"

    @api.model
    def _football_club_portal_configure_website(self):
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website:
            return

        if not website.homepage_url or website.homepage_url == "/":
            website.homepage_url = "/club"

        root_menu = website.menu_id
        if not root_menu:
            return

        self._football_club_portal_upsert_menu(root_menu, "Home", "/", 10)
        self._football_club_portal_upsert_menu(root_menu, "Events", "/club/events", 20)
        self._football_club_portal_upsert_menu(root_menu, "Join as a Fan", "/club/fan/register", 30)
        self._football_club_portal_upsert_menu(
            root_menu,
            "News",
            "/club#latest-club-updates",
            40,
            stale_domain=[("name", "=", "Club Home"), ("url", "=", "/club")],
        )
        self._football_club_portal_upsert_menu(root_menu, "About Us", "/club#about-club", 50)
        self._football_club_portal_upsert_menu(root_menu, "Contact Us", "/contactus", 60)

    @api.model
    def _football_club_portal_upsert_menu(self, root_menu, name, url, sequence, stale_domain=None):
        Menu = self.env["website.menu"]
        domain = [
            ("parent_id", "=", root_menu.id),
            ("website_id", "=", root_menu.website_id.id),
            ("url", "=", url),
        ]
        menu = Menu.search(domain, limit=1)
        if not menu and stale_domain:
            menu = Menu.search(
                [("parent_id", "=", root_menu.id), ("website_id", "=", root_menu.website_id.id)] + stale_domain,
                limit=1,
            )
        values = {
            "name": name,
            "url": url,
            "parent_id": root_menu.id,
            "website_id": root_menu.website_id.id,
            "sequence": sequence,
        }
        if menu:
            menu.write(values)
        else:
            Menu.create(values)
