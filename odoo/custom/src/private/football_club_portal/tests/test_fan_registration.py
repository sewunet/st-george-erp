import re
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestFanRegistration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Fan = cls.env["football.club.fan"]
        cls.Event = cls.env["football.club.event"]

    def _fan_values(self, **overrides):
        values = {
            "first_name": "Sam",
            "middle_name": "A.",
            "last_name": "Supporter",
            "email": " Sam.Supporter@example.COM ",
            "phone": " +251 (911) 123-456 ",
            "consent_accepted": True,
        }
        values.update(overrides)
        return values

    def test_fan_creation_assigns_registration_number_and_normalizes(self):
        fan = self.Fan.create(self._fan_values())
        self.assertNotEqual(fan.registration_number, "New")
        self.assertEqual(fan.name, "Sam A. Supporter")
        self.assertEqual(fan.normalized_email, "sam.supporter@example.com")
        self.assertEqual(fan.normalized_phone, "+251911123456")

    def test_full_name_is_first_middle_last(self):
        fan = self.Fan.create(self._fan_values(email="order@example.com", phone="+251911400000"))
        self.assertEqual(fan.name, " ".join([fan.first_name, fan.middle_name, fan.last_name]))

    def test_middle_name_is_required_by_the_database(self):
        # middle_name is NOT NULL, so a missing value is refused by PostgreSQL before
        # _check_required_names() ever runs. The savepoint keeps the cursor usable.
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"), self.cr.savepoint():
            self.Fan.create(self._fan_values(middle_name=False, email="nomiddle@example.com", phone="+251911410000"))

    def test_middle_name_cannot_be_whitespace_only(self):
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(middle_name="   ", email="blankmiddle@example.com", phone="+251911420000"))

    def test_last_name_cannot_be_whitespace_only(self):
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(last_name="   ", email="blanklast@example.com", phone="+251911430000"))

    def test_blanking_middle_name_on_an_existing_fan_is_rejected(self):
        fan = self.Fan.create(self._fan_values(email="edit@example.com", phone="+251911440000"))
        with self.assertRaises(ValidationError):
            fan.write({"middle_name": "  "})

    def test_partner_name_uses_the_full_fan_name(self):
        fan = self.Fan.create(self._fan_values(email="partner@example.com", phone="+251911450000"))
        self.assertTrue(fan.partner_id)
        self.assertEqual(fan.partner_id.name, "Sam A. Supporter")

    def test_contact_required(self):
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(email="", phone=""))

    def test_website_consent_required(self):
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(website_registration=True, consent_accepted=False))

    def test_duplicate_normalized_email_is_blocked(self):
        self.Fan.create(self._fan_values(email="fan@example.com", phone="+251911100000"))
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(email=" FAN@example.com ", phone="+251911100001"))

    def test_archived_duplicate_email_does_not_block_replacement(self):
        self.Fan.create(self._fan_values(email="archived@example.com", phone="+251911150000", active=False))
        replacement = self.Fan.create(self._fan_values(email=" archived@example.com ", phone="+251911150001"))
        self.assertTrue(replacement.active)

    def test_duplicate_normalized_phone_is_blocked(self):
        self.Fan.create(self._fan_values(email="phone-one@example.com", phone="+251 911 200 000"))
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(email="phone-two@example.com", phone="+251-911-200-000"))

    def test_future_birth_date_is_blocked(self):
        tomorrow = fields.Date.context_today(self.env.user) + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.Fan.create(self._fan_values(date_of_birth=tomorrow))

    def test_non_manager_cannot_force_sensitive_fan_state(self):
        user = new_test_user(
            self.env,
            login="football_club_user",
            groups="football_club_portal.group_football_club_user",
        )
        fan = self.Fan.create(self._fan_values(email="state@example.com", phone="+251911300000"))
        with self.assertRaises(AccessError):
            fan.with_user(user).write({"state": "suspended"})

    def test_event_public_visibility(self):
        event = self.Event.create({
            "name": "Opening Match",
            "event_type": "match",
            "start_datetime": fields.Datetime.now(),
            "state": "published",
            "website_published": True,
        })
        self.assertTrue(event._is_publicly_visible())

        draft_event = self.Event.create({
            "name": "Training Session",
            "event_type": "training",
            "start_datetime": fields.Datetime.now(),
        })
        self.assertFalse(draft_event._is_publicly_visible())

        cancelled_event = self.Event.create({
            "name": "Cancelled Gathering",
            "event_type": "fan_gathering",
            "start_datetime": fields.Datetime.now(),
            "state": "cancelled",
            "website_published": False,
        })
        self.assertFalse(cancelled_event._is_publicly_visible())

    def test_non_manager_cannot_publish_event_by_direct_write(self):
        user = new_test_user(
            self.env,
            login="football_club_event_user",
            groups="football_club_portal.group_football_club_user",
        )
        event = self.Event.create({
            "name": "Private Draft",
            "event_type": "other",
            "start_datetime": fields.Datetime.now(),
        })
        with self.assertRaises(AccessError):
            event.with_user(user).write({"state": "published", "website_published": True})


@tagged("-at_install", "post_install")
class TestFanRegistrationController(HttpCase):
    """End-to-end checks for fan authentication and registration routes."""

    AUTH_URL = "/club/fan/auth"
    REGISTER_URL = "/club/fan/register"
    PASSWORD = "StrongPass123"

    def setUp(self):
        super().setUp()
        self.Fan = self.env["football.club.fan"]
        self.Users = self.env["res.users"]

    def _csrf_token(self, url):
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
        self.assertTrue(match, f"Could not read the CSRF token from {url}.")
        return match.group(1)

    def _post_auth(self, email, password=None, **extra):
        payload = {
            "csrf_token": self._csrf_token(self.AUTH_URL),
            "email": email,
            "password": self.PASSWORD if password is None else password,
        }
        payload.update(extra)
        response = self.url_open(self.AUTH_URL, data=payload)
        self.env.invalidate_all()
        return response

    def _create_user(self, login, password=None, groups="base.group_portal"):
        return new_test_user(
            self.env,
            login=login,
            password=password or self.PASSWORD,
            groups=groups,
        )

    def _post_registration(self, **overrides):
        payload = {
            "csrf_token": self._csrf_token(self.REGISTER_URL),
            "first_name": "Web",
            "middle_name": "Test",
            "last_name": "Visitor",
            "email": "web.visitor@example.com",
            "phone": "+251911500000",
            "consent_accepted": "on",
        }
        payload.update(overrides)
        payload = {key: value for key, value in payload.items() if value is not None}
        response = self.url_open(self.REGISTER_URL, data=payload)
        self.assertEqual(response.status_code, 200)
        self.env.invalidate_all()
        return response

    def _fans_for(self, email):
        return self.Fan.search([("normalized_email", "=", email)])

    def _welcome_mails_for(self, email):
        return self.env["mail.mail"].sudo().search([
            ("subject", "=", "Welcome to St. George Sports Club"),
            ("email_to", "=", email),
        ])

    def test_public_club_pages_remain_public(self):
        self.assertEqual(self.url_open("/club").status_code, 200)
        self.assertEqual(self.url_open("/club/events").status_code, 200)
        event = self.env["football.club.event"].create({
            "name": "Public Test Match",
            "event_type": "match",
            "start_datetime": fields.Datetime.now(),
            "state": "published",
            "website_published": True,
        })
        self.assertEqual(self.url_open(f"/club/events/{event.id}").status_code, 200)

    def test_anonymous_registration_redirects_to_custom_auth(self):
        response = self.url_open(self.REGISTER_URL, allow_redirects=False)
        self.assertIn(response.status_code, (302, 303))
        self.assertTrue(response.headers["Location"].endswith(self.AUTH_URL))
        auth_response = self.url_open(self.AUTH_URL)
        self.assertIn("Email verification is not required at this stage.", auth_response.text)
        repeated_auth_response = self.url_open(self.AUTH_URL)
        self.assertIn("Email verification is not required at this stage.", repeated_auth_response.text)

    def test_new_account_is_normalized_portal_and_uses_expected_partner(self):
        response = self._post_auth(" New.Fan@Example.COM ")
        self.assertTrue(response.url.endswith(self.REGISTER_URL))
        user = self.Users.search([("login", "=", "new.fan@example.com")])
        self.assertEqual(len(user), 1)
        self.assertTrue(user._is_portal())
        self.assertFalse(user._is_internal())
        self.assertIn(self.env.ref("base.group_portal"), user.group_ids)
        self.assertNotIn(self.env.ref("base.group_user"), user.group_ids)
        self.assertEqual(user.partner_id.email, "new.fan@example.com")

    def test_new_account_does_not_reuse_an_email_matching_contact(self):
        partner = self.env["res.partner"].create({
            "name": "Existing Contact",
            "email": " Reuse.Partner@Example.COM ",
            "phone": "+251911000111",
        })
        original_values = partner.read(["name", "email", "phone"])[0]
        self._post_auth(" Reuse.Partner@example.com ")
        user = self.Users.search([("login", "=", "reuse.partner@example.com")])
        self.assertNotEqual(user.partner_id, partner)
        self.assertEqual(user.partner_id.email, "reuse.partner@example.com")
        self.assertEqual(partner.read(["name", "email", "phone"])[0], original_values)
        self.assertNotIn(user, partner.with_context(active_test=False).user_ids)

    def test_self_registered_account_can_log_in_again(self):
        login = "returning.new.fan@example.com"
        self._post_auth(login)
        self.assertTrue(self.Users.search([("login", "=", login)]))
        self.logout()
        response = self._post_auth(login)
        self.assertTrue(response.url.endswith(self.REGISTER_URL))
        self.assertEqual(self.Users.search_count([("login", "=", login)]), 1)

    def test_welcome_email_is_queued_only_for_new_account(self):
        login = "welcome.mail.fan@example.com"
        template = self.env.ref("football_club_portal.mail_template_portal_account_welcome")
        self.assertEqual(template.model, "res.users")
        initial_count = len(self._welcome_mails_for(login))

        self._post_auth(login)
        welcome_mails = self._welcome_mails_for(login)
        self.assertEqual(len(welcome_mails), initial_count + 1)
        self.assertNotIn(self.PASSWORD, welcome_mails[-1].body_html)

        self.logout()
        self._post_auth(login)
        self.assertEqual(len(self._welcome_mails_for(login)), initial_count + 1)

    def test_existing_portal_user_correct_password_logs_in_without_duplication(self):
        login = "existing.portal@example.com"
        user = self._create_user(login)
        response = self._post_auth(login)
        self.assertTrue(response.url.endswith(self.REGISTER_URL))
        self.assertEqual(self.Users.search_count([("login", "=", login)]), 1)
        self.assertTrue(user._is_portal())

    def test_existing_portal_user_wrong_password_is_rejected(self):
        login = "wrong.password@example.com"
        self._create_user(login)
        response = self._post_auth(login, password="IncorrectPass123")
        self.assertTrue(response.url.endswith(self.AUTH_URL))
        self.assertIn("Incorrect email or password.", response.text)
        self.assertEqual(self.Users.search_count([("login", "=", login)]), 1)

    def test_existing_internal_user_is_not_converted(self):
        login = "existing.internal@example.com"
        user = self._create_user(login, groups="base.group_user")
        original_groups = user.group_ids
        response = self._post_auth(login)
        self.assertTrue(response.url.endswith(self.REGISTER_URL))
        self.assertTrue(user._is_internal())
        self.assertFalse(user._is_portal())
        self.assertEqual(user.group_ids, original_groups)
        self.assertEqual(self.Users.search_count([("login", "=", login)]), 1)

    def test_internal_user_fan_update_preserves_partner_identity_and_groups(self):
        login = "internal.fan.identity@example.com"
        user = self._create_user(login, groups="base.group_user")
        partner = user.partner_id
        partner.write({
            "name": "Internal Club Staff",
            "email": login,
            "phone": False,
            "city": False,
        })
        original_groups = user.group_ids
        original_partner_values = partner.read(["name", "email", "phone", "city"])[0]
        fan = self.Fan.create({
            "partner_id": partner.id,
            "first_name": "Initial",
            "middle_name": "Internal",
            "last_name": "Fan",
            "email": "initial.internal.fan@example.com",
            "phone": "+251911600000",
            "consent_accepted": True,
        })

        self._post_auth(login)
        response = self._post_registration(
            first_name="Updated",
            email="updated.internal.fan@example.com",
            phone="+251911600001",
            city="Fan Registration City",
        )
        self.assertTrue(response.url.endswith("/club/fan/register/success"))

        self.env.invalidate_all()
        self.assertEqual(fan.partner_id, partner)
        self.assertEqual(fan.first_name, "Updated")
        self.assertEqual(fan.email, "updated.internal.fan@example.com")
        self.assertEqual(partner.read(["name", "email", "phone", "city"])[0], original_partner_values)
        self.assertEqual(user.group_ids, original_groups)
        self.assertTrue(user._is_internal())
        self.assertFalse(user._is_portal())

    def test_malformed_email_is_rejected(self):
        for email in ("abc", "abc@", "@example.com", "   "):
            response = self._post_auth(email)
            self.assertIn("Enter a valid email address.", response.text)
            self.assertFalse(self.Users.search([("login", "=", email.strip().lower())]))

    def test_empty_and_short_passwords_are_rejected(self):
        empty_response = self._post_auth("empty.password@example.com", password="")
        self.assertIn("Password is required.", empty_response.text)
        short_response = self._post_auth("short.password@example.com", password="short")
        self.assertIn("Password must be at least 8 characters.", short_response.text)
        self.assertFalse(self.Users.search([
            ("login", "in", ["empty.password@example.com", "short.password@example.com"]),
        ]))

    def test_auth_post_cannot_grant_privileged_fields(self):
        login = "mass.assignment@example.com"
        self._post_auth(
            login,
            groups_id="base.group_system",
            group_ids="base.group_user",
            share="0",
            active="0",
            company_ids="1",
            company_id="1",
            is_admin="1",
        )
        user = self.Users.search([("login", "=", login)])
        self.assertTrue(user._is_portal())
        self.assertFalse(user._is_internal())
        self.assertTrue(user.active)
        self.assertEqual(user.group_ids, self.env.ref("base.group_portal"))

    def test_registration_succeeds_with_the_full_name(self):
        login = "web.identity@example.com"
        self._post_auth(login)
        response = self._post_registration()
        self.assertTrue(response.url.endswith("/club/fan/register/success"))
        fan = self._fans_for("web.visitor@example.com")
        self.assertEqual(len(fan), 1)
        self.assertEqual(fan.middle_name, "Test")
        self.assertEqual(fan.last_name, "Visitor")
        self.assertEqual(fan.name, "Web Test Visitor")
        self.assertTrue(fan.website_registration)
        self.assertEqual(fan.partner_id, self.Users.search([("login", "=", login)]).partner_id)

    def test_registration_fails_without_middle_name(self):
        self._post_auth("missing.middle.identity@example.com")
        response = self._post_registration(middle_name=None, email="missing.middle@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("missing.middle@example.com"))

    def test_registration_fails_with_whitespace_only_middle_name(self):
        self._post_auth("blank.middle.identity@example.com")
        response = self._post_registration(middle_name="   ", email="blank.middle@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("blank.middle@example.com"))

    def test_registration_fails_without_last_name(self):
        self._post_auth("missing.last.identity@example.com")
        response = self._post_registration(last_name=None, email="missing.last@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("missing.last@example.com"))

    def test_registration_fails_with_whitespace_only_last_name(self):
        self._post_auth("blank.last.identity@example.com")
        response = self._post_registration(last_name="   ", email="blank.last@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("blank.last@example.com"))

    def test_registration_ignores_non_whitelisted_fields(self):
        self._post_auth("fan.whitelist.identity@example.com")
        self._post_registration(
            email="whitelist.fan@example.com",
            phone="+251911510000",
            state="active",
            registration_number="HACKED",
            website_registration="",
        )
        fan = self._fans_for("whitelist.fan@example.com")
        self.assertEqual(len(fan), 1)
        self.assertEqual(fan.state, "draft")
        self.assertNotEqual(fan.registration_number, "HACKED")

    def test_registration_still_blocks_duplicate_email(self):
        self.Fan.create({
            "first_name": "Existing",
            "middle_name": "Duplicate",
            "last_name": "Fan",
            "email": "dupe.fan@example.com",
            "phone": "+251911520000",
            "consent_accepted": True,
        })
        self._post_auth("dupe.identity@example.com")
        response = self._post_registration(email="DUPE.FAN@example.com", phone="+251911520001")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertEqual(len(self._fans_for("dupe.fan@example.com")), 1)

    def test_registration_still_blocks_duplicate_phone(self):
        self.Fan.create({
            "first_name": "Existing",
            "middle_name": "Phone",
            "last_name": "Fan",
            "email": "phone.one@example.com",
            "phone": "+251911530000",
            "consent_accepted": True,
        })
        self._post_auth("phone.identity@example.com")
        response = self._post_registration(email="phone.two@example.com", phone="+251-911-530-000")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("phone.two@example.com"))

    def test_repeated_registration_updates_same_partner_fan(self):
        login = "repeat.identity@example.com"
        self._post_auth(login)
        self._post_registration(email="repeat.fan@example.com", phone="+251911540000")
        user = self.Users.search([("login", "=", login)])
        fan = self.Fan.search([("partner_id", "=", user.partner_id.id)])
        self.assertEqual(len(fan), 1)

        response = self._post_registration(
            first_name="Updated",
            email="repeat.fan@example.com",
            phone="+251911540000",
        )
        self.assertTrue(response.url.endswith("/club/fan/register/success"))
        fans = self.Fan.with_context(active_test=False).search([("partner_id", "=", user.partner_id.id)])
        self.assertEqual(len(fans), 1)
        self.assertEqual(fans.first_name, "Updated")
