import logging

from psycopg2 import IntegrityError
from werkzeug.urls import urlencode

from odoo import Command, fields, http
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request
from odoo.tools import escape_psql, single_email_re


_logger = logging.getLogger(__name__)


class FootballClubPortal(http.Controller):
    _fan_auth_url = "/club/fan/auth"
    _fan_register_url = "/club/fan/register"
    _minimum_password_length = 8
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

    def _normalize_login(self, email):
        return (email or "").strip().lower()

    def _is_plausible_email(self, email):
        return bool(single_email_re.fullmatch(email))

    def _authenticate(self, login, password):
        credential = {"login": login, "password": password, "type": "password"}
        return request.session.authenticate(request.env, credential)

    def _find_user_by_login(self, login):
        Users = request.env["res.users"].sudo().with_context(active_test=False)
        user = Users.search([("login", "=", login)], limit=1)
        if user:
            return user
        candidates = Users.search([("login", "=ilike", escape_psql(login))], order="id")
        return candidates.filtered(lambda candidate: self._normalize_login(candidate.login) == login)[:1]

    def _create_portal_user(self, login, password):
        partner = request.env["res.partner"].sudo().create({"name": login, "email": login})
        portal_group = request.env.ref("base.group_portal").sudo()
        return request.env["res.users"].sudo().with_context(no_reset_password=True).create({
            "name": partner.name or login,
            "login": login,
            "email": login,
            "partner_id": partner.id,
            "password": password,
            "group_ids": [Command.set([portal_group.id])],
        })

    def _send_portal_welcome_email(self, user):
        template = request.env.ref(
            "football_club_portal.mail_template_portal_account_welcome",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning("Portal account welcome mail template is unavailable")
            return
        try:
            template.sudo().send_mail(user.id, force_send=False, raise_exception=False)
        except Exception:
            _logger.exception("Unable to queue portal account welcome email for user ID %s", user.id)

    def _fan_for_current_partner(self):
        if request.env.user._is_public():
            return request.env["football.club.fan"].browse()
        return request.env["football.club.fan"].sudo().with_context(active_test=False).search(
            [("partner_id", "=", request.env.user.partner_id.id)],
            order="active desc, id",
            limit=1,
        )

    def _fan_values(self, fan):
        if not fan:
            return {}
        values = {field_name: fan[field_name] or "" for field_name in self._fan_allowed_fields}
        for field_name in ("date_of_birth", "supporter_since"):
            values[field_name] = fields.Date.to_string(fan[field_name]) if fan[field_name] else ""
        values["consent_accepted"] = fan.consent_accepted
        return values

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

    @http.route(
        "/club/fan/auth",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        csrf=True,
        methods=["GET", "POST"],
    )
    def fan_auth(self, **post):
        if not request.env.user._is_public():
            return request.redirect("/club" if self._fan_for_current_partner() else self._fan_register_url)

        login = self._normalize_login(post.get("email"))
        error = False
        if request.httprequest.method == "POST":
            password = post.get("password") or ""
            if not self._is_plausible_email(login):
                error = "Enter a valid email address."
            elif not password:
                error = "Password is required."
            elif len(password) < self._minimum_password_length:
                error = f"Password must be at least {self._minimum_password_length} characters."
            else:
                new_account_created = False
                user = self._find_user_by_login(login)
                if not user:
                    try:
                        with request.env.cr.savepoint():
                            user = self._create_portal_user(login, password)
                        new_account_created = True
                    except (IntegrityError, ValidationError):
                        request.env.invalidate_all()
                        user = self._find_user_by_login(login)
                    except Exception:
                        _logger.exception("Unexpected fan account creation failure for normalized login %s", login)
                        error = "We could not complete sign-in. Please try again later."

                if user and not error:
                    try:
                        auth_info = self._authenticate(login, password)
                        if auth_info.get("uid") == request.session.uid:
                            if new_account_created:
                                self._send_portal_welcome_email(user)
                            return request.redirect(
                                "/club" if self._fan_for_current_partner() else self._fan_register_url
                            )
                        error = "Additional account verification is required. Please use the standard sign-in page."
                    except AccessDenied:
                        error = "Incorrect email or password."
                    except Exception:
                        _logger.exception("Unexpected fan authentication failure for normalized login %s", login)
                        error = "We could not complete sign-in. Please try again later."
                elif not error:
                    error = "Incorrect email or password."

        return request.render(
            "football_club_portal.fan_auth",
            {"email": login, "error": error, "minimum_password_length": self._minimum_password_length},
        )

    @http.route("/club/fan/register", type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def fan_register(self, **post):
        if request.env.user._is_public():
            return request.redirect(self._fan_auth_url)

        fan = self._fan_for_current_partner()
        values = self._fan_values(fan)
        errors = {}
        if request.httprequest.method == "POST":
            values = {field_name: post.get(field_name, "") for field_name in self._fan_allowed_fields}
            values["consent_accepted"] = post.get("consent_accepted") in {"on", "1", "true", "True", "yes"}
            create_values, errors = self._prepare_fan_values(post)
            values.update(create_values)
            errors.update(self._fan_form_errors(create_values))
            if not errors:
                try:
                    with request.env.cr.savepoint():
                        if fan:
                            fan.write(create_values)
                        else:
                            create_values["partner_id"] = request.env.user.partner_id.id
                            fan = request.env["football.club.fan"].sudo().create(create_values)
                    return request.redirect("/club/fan/register/success")
                except ValidationError as error:
                    errors["general"] = error.args[0] if error.args else "Please review the registration form."
                except Exception:
                    _logger.exception("Unexpected website fan registration failure")
                    errors["general"] = "We could not complete the registration. Please try again later."
        return request.render(
            "football_club_portal.fan_registration_form",
            {
                "values": values,
                "errors": errors,
                "fan": fan,
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
