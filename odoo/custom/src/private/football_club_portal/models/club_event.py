import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html2plaintext


class FootballClubEvent(models.Model):
    _name = "football.club.event"
    _description = "Football Club Event"
    _inherit = ["mail.thread", "mail.activity.mixin", "website.published.mixin"]
    _rec_name = "name"
    _order = "start_datetime asc, id desc"

    name = fields.Char(required=True, tracking=True)
    slug = fields.Char(compute="_compute_slug", store=True, index=True)
    event_type = fields.Selection(
        [
            ("match", "Match"),
            ("fan_gathering", "Fan Gathering"),
            ("training", "Training"),
            ("charity", "Charity"),
            ("meet_and_greet", "Meet and Greet"),
            ("announcement", "Announcement"),
            ("other", "Other"),
        ],
        default="match",
        required=True,
    )
    short_description = fields.Text()
    description = fields.Html(sanitize=True)
    start_datetime = fields.Datetime(required=True, tracking=True)
    end_datetime = fields.Datetime()
    venue = fields.Char()
    address = fields.Text()
    cover_image = fields.Image(max_width=1920, max_height=1080)
    registration_required = fields.Boolean()
    maximum_attendees = fields.Integer()
    website_url = fields.Char(compute="_compute_website_url")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("published", "Published"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    @api.model
    def _slugify_name(self, name):
        value = (name or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-") or False

    @api.depends("name")
    def _compute_slug(self):
        for event in self:
            event.slug = event._slugify_name(event.name) if event.name else False

    def _compute_website_url(self):
        for event in self:
            event.website_url = f"/club/events/{event.id}" if event.id else False

    def _is_football_club_manager(self):
        return self.env.is_superuser() or self.env.user.has_group("football_club_portal.group_football_club_manager")

    def _ensure_manager(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can publish or change publication state."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state") not in (None, False, "draft") or vals.get("website_published"):
                self._ensure_manager()
        return super().create(vals_list)

    def write(self, vals):
        if {"state", "website_published"}.intersection(vals):
            self._ensure_manager()
        return super().write(vals)

    @api.constrains("start_datetime", "end_datetime")
    def _check_dates(self):
        for event in self:
            if not event.start_datetime:
                raise ValidationError(_("Start datetime is required."))
            if event.end_datetime and event.end_datetime < event.start_datetime:
                raise ValidationError(_("End datetime cannot be earlier than start datetime."))

    @api.constrains("maximum_attendees")
    def _check_maximum_attendees(self):
        for event in self:
            if event.maximum_attendees < 0:
                raise ValidationError(_("Maximum attendees cannot be negative."))

    @api.constrains("name", "state", "website_published")
    def _check_published_name(self):
        for event in self:
            if event.state == "published" and not (event.name or "").strip():
                raise ValidationError(_("Published events must have a meaningful name."))

    def _is_publicly_visible(self):
        self.ensure_one()
        return bool(self.active and self.state == "published" and self.website_published)

    def _get_public_description_text(self):
        self.ensure_one()
        return html2plaintext(self.description or "")

    def _ensure_state(self, allowed_states):
        invalid = self.filtered(lambda event: event.state not in allowed_states)
        if invalid:
            raise ValidationError(_("The selected event state transition is not allowed."))

    def action_publish(self):
        self._ensure_manager()
        self._ensure_state({"draft"})
        self.write({"state": "published", "website_published": True})

    def action_unpublish(self):
        self._ensure_manager()
        self._ensure_state({"published"})
        self.write({"state": "draft", "website_published": False})

    def action_complete(self):
        self._ensure_manager()
        self._ensure_state({"published"})
        self.write({"state": "completed", "website_published": False})

    def action_cancel(self):
        self._ensure_manager()
        self._ensure_state({"draft", "published"})
        self.write({"state": "cancelled", "website_published": False})

    def action_reset_to_draft(self):
        self._ensure_manager()
        self._ensure_state({"published", "completed", "cancelled"})
        self.write({"state": "draft", "website_published": False})

    def unlink(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can delete event records."))
        return super().unlink()

