import uuid

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()

PASSWORD = "test-pass-12345"


class UserModelTests(TestCase):
    def test_settings_point_to_custom_user(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertIs(get_user_model(), User)
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(" Student@Example.COM ", PASSWORD)

        self.assertEqual(user.email, "student@example.com")
        self.assertEqual(user.full_name, "")
        self.assertIsInstance(user.pk, uuid.UUID)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertIsNotNone(user.date_joined)

    def test_save_normalizes_email(self):
        user = User.objects.create_user("first@example.com", PASSWORD)
        user.email = " First@Example.COM "
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.email, "first@example.com")

    def test_full_name_can_be_filled_later(self):
        user = User.objects.create_user("later@example.com", PASSWORD)
        user.full_name = "Иванов Иван"
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.full_name, "Иванов Иван")
        self.assertEqual(user.get_full_name(), "Иванов Иван")

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("   ", PASSWORD)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(" Root@Example.COM ", PASSWORD)

        self.assertEqual(admin.email, "root@example.com")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.check_password(PASSWORD))

    def test_superuser_flags_cannot_be_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                "root@example.com", PASSWORD, is_staff=False
            )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                "root@example.com", PASSWORD, is_superuser=False
            )

    def test_case_insensitive_duplicate_is_rejected(self):
        User.objects.create_user("ivan@example.com", PASSWORD)

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("IVAN@EXAMPLE.COM", PASSWORD)

        self.assertEqual(User.objects.count(), 1)

    def test_database_rejects_different_case_without_normalization(self):
        User.objects.create_user("ivan@example.com", PASSWORD)

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create(
                [User(email="IVAN@EXAMPLE.COM", password="not-a-real-hash")]
            )

        self.assertEqual(User.objects.count(), 1)

    def test_authentication_ignores_email_case(self):
        user = User.objects.create_user("student@example.com", PASSWORD)

        found = authenticate(username="STUDENT@EXAMPLE.COM", password=PASSWORD)

        self.assertEqual(found, user)
