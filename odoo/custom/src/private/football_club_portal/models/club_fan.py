import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


_logger = logging.getLogger(__name__)


class FootballClubFan(models.Model):
    _name = "football.club.fan"
    _description = "Football Club Fan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "registration_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True, tracking=True)
    registration_number = fields.Char(
        default="New",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Related Contact",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    first_name = fields.Char(required=True, tracking=True)
    middle_name = fields.Char(required=True)
    # last_name carries the fan's grandfather's name in this project; the public
    # registration form labels it accordingly.
    last_name = fields.Char(required=True, tracking=True)
    email = fields.Char()
    normalized_email = fields.Char(compute="_compute_normalized_contacts", store=True, index=True)
    phone = fields.Char()
    normalized_phone = fields.Char(compute="_compute_normalized_contacts", store=True, index=True)
    gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not_to_say", "Prefer not to say"),
        ]
    )
    date_of_birth = fields.Date()
    city = fields.Char()
    favorite_player = fields.Char()
    supporter_since = fields.Date()
    preferred_communication = fields.Selection(
        [
            ("email", "Email"),
            ("phone", "Phone"),
            ("sms", "SMS"),
            ("none", "None"),
        ],
        default="email",
    )
    profile_image = fields.Image(max_width=1024, max_height=1024)
    registration_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    website_registration = fields.Boolean(default=False, readonly=True)
    consent_accepted = fields.Boolean()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.depends("first_name", "middle_name", "last_name")
    def _compute_name(self):
        for fan in self:
            fan.name = fan._build_display_name(fan.first_name, fan.middle_name, fan.last_name)

    @api.depends("email", "phone")
    def _compute_normalized_contacts(self):
        for fan in self:
            fan.normalized_email = self._normalize_email(fan.email)
            fan.normalized_phone = self._normalize_phone(fan.phone)

    @api.model
    def _build_display_name(self, first_name, middle_name, last_name):
        parts = [part.strip() for part in [first_name or "", middle_name or "", last_name or ""] if part and part.strip()]
        return " ".join(parts)

    @api.model
    def _normalize_email(self, email):
        return (email or "").strip().lower() or False

    @api.model
    def _normalize_phone(self, phone):
        value = (phone or "").strip()
        if not value:
            return False
        leading_plus = value.startswith("+")
        cleaned = re.sub(r"[\s\-().]", "", value)
        cleaned = re.sub(r"[^0-9+]", "", cleaned)
        cleaned = cleaned.replace("+", "")
        if not cleaned:
            return False
        return f"+{cleaned}" if leading_plus else cleaned

    def _is_football_club_manager(self):
        return self.env.is_superuser() or self.env.user.has_group("football_club_portal.group_football_club_manager")

    def _check_state_write_allowed(self, vals):
        if "state" not in vals or self._is_football_club_manager():
            return
        target_state = vals.get("state")
        allowed_transitions = {("draft", "confirmed"), ("draft", "active"), ("confirmed", "active")}
        for fan in self:
            if (fan.state, target_state) not in allowed_transitions:
                raise AccessError(_("Only Football Club managers can perform this fan state change."))

    @api.model
    def _prepare_partner_values(self, vals):
        name = self._build_display_name(vals.get("first_name"), vals.get("middle_name"), vals.get("last_name"))
        return {
            "name": name or _("Football Club Fan"),
            "email": (vals.get("email") or "").strip() or False,
            "phone": (vals.get("phone") or "").strip() or False,
            "city": (vals.get("city") or "").strip() or False,
        }

    @api.model
    def _partner_has_internal_user(self, partner):
        users = partner.sudo().with_context(active_test=False).user_ids
        return any(user._is_internal() for user in users)

    @api.model
    def _find_matching_partner(self, vals):
        Partner = self.env["res.partner"].sudo()
        email = self._normalize_email(vals.get("email"))
        phone = self._normalize_phone(vals.get("phone"))
        if email:
            partner = Partner.search([("email", "=ilike", email)], order="id", limit=1)
            if partner:
                return partner
        if phone:
            partners = Partner.search([("phone", "!=", False)], order="id")
            for partner in partners:
                if self._normalize_phone(partner.phone) == phone:
                    return partner
        return Partner.browse()

    @api.model
    def _get_or_create_partner(self, vals):
        partner = self._find_matching_partner(vals)
        partner_values = self._prepare_partner_values(vals)
        if partner:
            updates = {}
            if not self._partner_has_internal_user(partner):
                updates = {key: value for key, value in partner_values.items() if value and not partner[key]}
            if updates:
                partner.write(updates)
            return partner
        return self.env["res.partner"].sudo().create(partner_values)

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("state") and vals["state"] != "draft" and not self._is_football_club_manager():
                raise AccessError(_("Only Football Club managers can create fans outside the draft state."))
            if vals.get("registration_number", "New") == "New":
                vals["registration_number"] = self.env["ir.sequence"].next_by_code("football.club.fan") or "New"
            if not vals.get("partner_id"):
                vals["partner_id"] = self._get_or_create_partner(vals).id
            prepared_vals.append(vals)
        fans = super().create(prepared_vals)
        fans.filtered(lambda fan: fan.website_registration and fan.email)._send_registration_email()
        return fans

    def write(self, vals):
        self._check_state_write_allowed(vals)
        result = super().write(vals)
        sync_fields = {"email", "phone", "city", "first_name", "middle_name", "last_name"}
        if sync_fields.intersection(vals):
            for fan in self.filtered("partner_id"):
                if self._partner_has_internal_user(fan.partner_id):
                    continue
                partner_updates = {}
                if "email" in vals and fan.email and not fan.partner_id.email:
                    partner_updates["email"] = fan.email.strip()
                if "phone" in vals and fan.phone and not fan.partner_id.phone:
                    partner_updates["phone"] = fan.phone.strip()
                if "city" in vals and fan.city and not fan.partner_id.city:
                    partner_updates["city"] = fan.city.strip()
                if {"first_name", "middle_name", "last_name"}.intersection(vals) and fan.name and not fan.partner_id.name:
                    partner_updates["name"] = fan.name
                if partner_updates:
                    fan.partner_id.sudo().write(partner_updates)
        return result

    def unlink(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can delete fan records."))
        return super().unlink()

    @api.constrains("first_name", "middle_name", "last_name")
    def _check_required_names(self):
        """Reject blank or whitespace-only parts of the first + middle + last name.

        All three columns are NOT NULL, so the database already rejects missing values.
        This adds the check it cannot make: "   " satisfies NOT NULL but is not a name.
        """
        for fan in self:
            if not (fan.first_name or "").strip():
                raise ValidationError(_("First name cannot be blank."))
            if not (fan.middle_name or "").strip():
                raise ValidationError(_("Middle name cannot be blank."))
            if not (fan.last_name or "").strip():
                raise ValidationError(_("Grandfather's name (last name) cannot be blank."))

    @api.constrains("email", "phone")
    def _check_contact_required_and_format(self):
        for fan in self:
            if not fan.normalized_email and not fan.normalized_phone:
                raise ValidationError(_("Provide at least one contact method: email or phone."))
            if fan.email:
                email = fan.normalized_email
                if "@" not in email or email.startswith("@") or email.endswith("@") or "." not in email.rsplit("@", 1)[-1]:
                    raise ValidationError(_("Enter a valid email address."))

    @api.constrains("website_registration", "consent_accepted")
    def _check_website_consent(self):
        for fan in self:
            if fan.website_registration and not fan.consent_accepted:
                raise ValidationError(_("You must accept the consent statement to register."))

    @api.constrains("date_of_birth")
    def _check_date_of_birth(self):
        today = fields.Date.context_today(self)
        for fan in self:
            if fan.date_of_birth and fan.date_of_birth > today:
                raise ValidationError(_("Date of birth cannot be in the future."))

    @api.constrains("normalized_email", "normalized_phone", "active")
    def _check_duplicate_contacts(self):
        for fan in self:
            if not fan.active:
                continue
            if fan.normalized_email:
                duplicate = self.search_count([
                    ("id", "!=", fan.id),
                    ("active", "=", True),
                    ("normalized_email", "=", fan.normalized_email),
                ])
                if duplicate:
                    raise ValidationError(_("An active fan registration already exists with this email."))
            if fan.normalized_phone:
                duplicate = self.search_count([
                    ("id", "!=", fan.id),
                    ("active", "=", True),
                    ("normalized_phone", "=", fan.normalized_phone),
                ])
                if duplicate:
                    raise ValidationError(_("An active fan registration already exists with this phone number."))

    def _ensure_state(self, allowed_states):
        invalid = self.filtered(lambda fan: fan.state not in allowed_states)
        if invalid:
            raise ValidationError(_("The selected state transition is not allowed."))

    def action_confirm(self):
        self._ensure_state({"draft"})
        self.write({"state": "confirmed"})

    def action_activate(self):
        allowed_states = {"draft", "confirmed", "suspended"} if self._is_football_club_manager() else {"draft", "confirmed"}
        self._ensure_state(allowed_states)
        self.write({"state": "active"})

    def action_suspend(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can suspend fans."))
        self._ensure_state({"confirmed", "active"})
        self.write({"state": "suspended"})

    def action_reject(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can reject fans."))
        self._ensure_state({"draft", "confirmed"})
        self.write({"state": "rejected"})

    def action_reset_to_draft(self):
        if not self._is_football_club_manager():
            raise AccessError(_("Only Football Club managers can reset fans to draft."))
        self._ensure_state({"confirmed", "active", "suspended", "rejected"})
        self.write({"state": "draft"})

    def _send_registration_email(self):
        template = self.env.ref("football_club_portal.mail_template_fan_registration", raise_if_not_found=False)
        if not template:
            return
        for fan in self.filtered("email"):
            try:
                template.sudo().send_mail(fan.id, force_send=False, raise_exception=False)
            except Exception:
                _logger.exception("Unable to queue fan registration email for fan ID %s", fan.id)
