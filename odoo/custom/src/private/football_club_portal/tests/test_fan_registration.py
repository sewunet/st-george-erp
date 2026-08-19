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
    """End-to-end checks on the public /club/fan/register endpoint.

    These deliberately bypass the browser, so the HTML ``required`` attribute offers
    no protection: only the server-side validation is exercised.
    """

    REGISTER_URL = "/club/fan/register"

    def setUp(self):
        super().setUp()
        self.Fan = self.env["football.club.fan"]

    def _csrf_token(self):
        response = self.url_open(self.REGISTER_URL)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
        self.assertTrue(match, "Could not read the CSRF token from the registration form.")
        return match.group(1)

    def _post_registration(self, **overrides):
        payload = {
            "csrf_token": self._csrf_token(),
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

    def test_registration_succeeds_with_the_full_name(self):
        response = self._post_registration()
        self.assertTrue(response.url.endswith("/club/fan/register/success"))
        fan = self._fans_for("web.visitor@example.com")
        self.assertEqual(len(fan), 1)
        self.assertEqual(fan.middle_name, "Test")
        self.assertEqual(fan.last_name, "Visitor")
        self.assertEqual(fan.name, "Web Test Visitor")
        self.assertTrue(fan.website_registration)

    def test_registration_fails_without_middle_name(self):
        response = self._post_registration(middle_name=None, email="missing.middle@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("missing.middle@example.com"))

    def test_registration_fails_with_whitespace_only_middle_name(self):
        response = self._post_registration(middle_name="   ", email="blank.middle@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("blank.middle@example.com"))

    def test_registration_fails_without_last_name(self):
        response = self._post_registration(last_name=None, email="missing.last@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("missing.last@example.com"))

    def test_registration_fails_with_whitespace_only_last_name(self):
        response = self._post_registration(last_name="   ", email="blank.last@example.com")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("blank.last@example.com"))

    def test_registration_ignores_non_whitelisted_fields(self):
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
        self._post_registration(email="dupe.fan@example.com", phone="+251911520000")
        self.assertEqual(len(self._fans_for("dupe.fan@example.com")), 1)
        response = self._post_registration(email="DUPE.FAN@example.com", phone="+251911520001")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertEqual(len(self._fans_for("dupe.fan@example.com")), 1)

    def test_registration_still_blocks_duplicate_phone(self):
        self._post_registration(email="phone.one@example.com", phone="+251911530000")
        self.assertEqual(len(self._fans_for("phone.one@example.com")), 1)
        response = self._post_registration(email="phone.two@example.com", phone="+251-911-530-000")
        self.assertFalse(response.url.endswith("/club/fan/register/success"))
        self.assertFalse(self._fans_for("phone.two@example.com"))
