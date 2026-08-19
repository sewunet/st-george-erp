import logging

from werkzeug.urls import urlencode

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class FootballClubPortal(http.Controller):
    _fan_allowed_fields = {
        "first_name",
        "middle_name",
        "last_name",
        "email",
        "phone",
        "gender",
        "date_of_birth",
        "city",
        "favorite_player",
        "supporter_since",
        "preferred_communication",
    }

    def _event_domain(self, upcoming=False):
        domain = [
            ("active", "=", True),
            ("state", "=", "published"),
            ("website_published", "=", True),
        ]
        if upcoming:
            domain.append(("start_datetime", ">=", fields.Datetime.now()))
        return domain

    def _event_type_options(self):
        return request.env["football.club.event"]._fields["event_type"].selection

    def _events_url(self, search=None, event_type=None):
        args = {}
        if search:
            args["search"] = search
        if event_type:
            args["event_type"] = event_type
        query = urlencode(args)
        return f"/club/events?{query}" if query else "/club/events"

    def _selection_values(self, model_name, field_name):
        return {value for value, label in request.env[model_name]._fields[field_name].selection}

    def _parse_date_value(self, values, errors, field_name, label):
        value = (values.get(field_name) or "").strip()
        if not value:
            values[field_name] = False
            return
        try:
            values[field_name] = fields.Date.to_string(fields.Date.to_date(value))
        except (TypeError, ValueError):
            errors[field_name] = f"{label} is not a valid date."

    def _prepare_fan_values(self, post):
        values = {
            field_name: (post.get(field_name) or "").strip()
            for field_name in self._fan_allowed_fields
            if field_name in post
        }
        errors = {}
        gender_values = self._selection_values("football.club.fan", "gender")
        communication_values = self._selection_values("football.club.fan", "preferred_communication")

        if values.get("gender") and values["gender"] not in gender_values:
            errors["gender"] = "Select a valid gender option."
        if values.get("preferred_communication") and values["preferred_communication"] not in communication_values:
            errors["preferred_communication"] = "Select a valid communication option."

        self._parse_date_value(values, errors, "date_of_birth", "Date of birth")
        self._parse_date_value(values, errors, "supporter_since", "Supporter since")

        for optional_field in ("gender", "date_of_birth", "supporter_since", "preferred_communication", "city", "favorite_player"):
            if not values.get(optional_field):
                values.pop(optional_field, None)

        values["website_registration"] = True
        values["consent_accepted"] = post.get("consent_accepted") in {"on", "1", "true", "True", "yes"}
        return values, errors

    def _fan_form_errors(self, values):
        errors = {}
        if not values.get("first_name"):
            errors["first_name"] = "First name is required."
        if not values.get("middle_name"):
            errors["middle_name"] = "Middle name is required."
        if not values.get("last_name"):
            errors["last_name"] = "Grandfather's name is required."
        if not values.get("email") and not values.get("phone"):
            errors["contact"] = "Provide at least an email address or phone number."
        if not values.get("consent_accepted"):
            errors["consent_accepted"] = "Consent is required for registration."
        return errors

    @http.route("/club", type="http", auth="public", website=True, sitemap=True)
    def club_home(self, **kwargs):
        events = request.env["football.club.event"].sudo().search(
            self._event_domain(upcoming=True),
            order="start_datetime asc, id desc",
            limit=3,
        )
        return request.render("football_club_portal.club_home", {"events": events})

    @http.route("/club/fan/register", type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def fan_register(self, **post):
        values = {field_name: post.get(field_name, "") for field_name in self._fan_allowed_fields}
        values["consent_accepted"] = post.get("consent_accepted") in {"on", "1", "true", "True", "yes"}
        errors = {}
        if request.httprequest.method == "POST":
            create_values, errors = self._prepare_fan_values(post)
            values.update(create_values)
            errors.update(self._fan_form_errors(create_values))
            if not errors:
                try:
                    with request.env.cr.savepoint():
                        request.env["football.club.fan"].sudo().create(create_values)
                    return request.redirect("/club/fan/register/success")
                except ValidationError as error:
                    errors["general"] = error.args[0] if error.args else "Please review the registration form."
                except Exception:
                    _logger.exception("Unexpected public fan registration failure")
                    errors["general"] = "We could not complete the registration. Please try again later."
        return request.render(
            "football_club_portal.fan_registration_form",
            {
                "values": values,
                "errors": errors,
                "gender_options": request.env["football.club.fan"]._fields["gender"].selection,
                "communication_options": request.env["football.club.fan"]._fields["preferred_communication"].selection,
            },
        )

    @http.route("/club/fan/register/success", type="http", auth="public", website=True, sitemap=False)
    def fan_register_success(self, **kwargs):
        return request.render("football_club_portal.fan_registration_success", {})

    @http.route("/club/events", type="http", auth="public", website=True, sitemap=True)
    def club_events(self, page=1, event_type=None, search=None, **kwargs):
        try:
            page = max(int(page), 1)
        except (TypeError, ValueError):
            page = 1
        Event = request.env["football.club.event"].sudo()
        domain = self._event_domain()
        event_types = self._event_type_options()
        if event_type not in dict(event_types):
            event_type = None
        if event_type:
            domain.append(("event_type", "=", event_type))
        search = (search or "").strip()[:80]
        if search:
            domain += [
                "|",
                "|",
                ("name", "ilike", search),
                ("venue", "ilike", search),
                ("short_description", "ilike", search),
            ]
        url_args = {}
        if event_type:
            url_args["event_type"] = event_type
        if search:
            url_args["search"] = search
        total = Event.search_count(domain)
        pager = request.website.pager(
            url="/club/events",
            total=total,
            page=page,
            step=9,
            url_args=url_args or None,
        )
        events = Event.search(domain, order="start_datetime asc, id desc", limit=9, offset=pager["offset"])
        event_filter_links = [{"value": False, "label": "All", "url": self._events_url(search=search)}]
        event_filter_links += [
            {"value": value, "label": label, "url": self._events_url(search=search, event_type=value)}
            for value, label in event_types
        ]
        return request.render(
            "football_club_portal.event_listing",
            {
                "events": events,
                "pager": pager,
                "event_type": event_type,
                "event_types": event_types,
                "event_filter_links": event_filter_links,
                "search": search,
            },
        )

    @http.route("/club/events/<int:event_id>", type="http", auth="public", website=True, sitemap=False)
    def club_event_detail(self, event_id, **kwargs):
        event = request.env["football.club.event"].sudo().browse(event_id)
        if not event.exists() or not event._is_publicly_visible():
            return request.not_found()
        return request.render("football_club_portal.event_detail", {"event": event})
