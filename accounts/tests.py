from django.test import TestCase
from django.urls import reverse

from .models import User


class UserRoleTests(TestCase):
    def test_new_users_are_public(self):
        user = User.objects.create_user("alice", password="pw-12345-x")
        self.assertEqual(user.role, User.Role.PUBLIC)
        self.assertFalse(user.is_cemetery_staff)
        self.assertFalse(user.is_staff)

    def test_staff_role_grants_admin_site_access(self):
        user = User.objects.create_user("bob", password="pw-12345-x", role=User.Role.STAFF)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_cemetery_staff)
        self.assertFalse(user.is_site_admin)

    def test_superuser_counts_as_admin(self):
        user = User.objects.create_superuser("root", password="pw-12345-x")
        self.assertTrue(user.is_site_admin)
        self.assertTrue(user.is_cemetery_staff)


class SignUpViewTests(TestCase):
    def test_signup_creates_public_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "carol",
                "email": "carol@example.com",
                "first_name": "Carol",
                "last_name": "Adams",
                "password1": "a-long-Passphrase-42",
                "password2": "a-long-Passphrase-42",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user = User.objects.get(username="carol")
        self.assertEqual(user.role, User.Role.PUBLIC)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_role_cannot_be_chosen_at_signup(self):
        self.client.post(
            reverse("accounts:signup"),
            {
                "username": "mallory",
                "email": "m@example.com",
                "password1": "a-long-Passphrase-42",
                "password2": "a-long-Passphrase-42",
                "role": "admin",
            },
        )
        self.assertEqual(User.objects.get(username="mallory").role, User.Role.PUBLIC)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
