from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


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
