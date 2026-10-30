from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HeaderUserMenuTests(TestCase):
    """Шапка каталога: кружок пользователя с меню «Мой профиль» и «Выйти»."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="student@example.com",
            password="strong-pass-1",
            full_name="Иван Петров",
        )
        self.url = reverse("projects:catalog")

    def test_authenticated_user_sees_avatar_dropdown(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        html = response.content.decode()

        self.assertIn("catalog-user-menu", html)
        self.assertIn('aria-haspopup="menu"', html)
        self.assertIn('aria-label="Меню пользователя: Иван Петров"', html)
        self.assertIn(">И<", html)
        self.assertIn("Мой профиль", html)
        self.assertIn("aria-disabled=\"true\"", html)
        self.assertIn("Выйти", html)
        self.assertIn(reverse("accounts:logout"), html)

    def test_logout_button_is_not_shown_in_header_any_more(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertNotContains(response, "catalog-logout\"")

    def test_logout_from_menu_signs_user_out(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("main:catalog"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_guest_sees_login_link_without_menu(self):
        response = self.client.get(self.url)
        html = response.content.decode()

        self.assertNotIn("catalog-user-menu", html)
        self.assertIn(reverse("accounts:login"), html)

    def test_user_menu_is_shown_on_project_workflow_pages(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("projects:create"))

        self.assertContains(response, "catalog-user-menu")
        self.assertContains(response, "Выйти")
