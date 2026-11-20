"""Общий подвал: одинаковый блок и его стили на каждой странице приложения.

Регрессия: стили подвала жили в catalog.css, а страницы входа и регистрации
подключают только auth.css. Футер рендерился без оформления — белой полосой.
Теперь файл footer.css подключается через base.html и профиль.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from projects.models import Category, Project

FOOTER = (
    '<footer class="catalog-footer"><div><strong>studymate</strong> / сделаем вместе'
    "</div><span>Учебный проект · Ростелеком</span></footer>"
)


class FooterConsistencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("footer@example.com", "Password!1")
        cls.other = get_user_model().objects.create_user("other@example.com", "Password!1")
        category = Category.objects.create(name="Наука", slug="science")
        cls.project = Project.objects.create(author=cls.user, category=category, title="Проект")

    def assert_footer(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, FOOTER, count=1)
        self.assertContains(response, "css/footer.css")

    def test_guest_pages(self):
        # Гостевые страницы: вход и регистрация наследуют base.html.
        for name in ("login", "register"):
            with self.subTest(page=name):
                self.assert_footer(self.client.get(reverse(f"accounts:{name}")))

    def test_authenticated_pages(self):
        self.client.force_login(self.user)
        pages = [
            reverse("projects:catalog"),
            reverse("applications:mine"),
            reverse("projects:mine"),
            reverse("projects:detail", args=[self.project.pk]),
            reverse("applications:incoming", args=[self.project.pk]),
        ]
        for page in pages:
            with self.subTest(page=page):
                self.assert_footer(self.client.get(page))

    def test_profile_page_links_footer_stylesheet(self):
        # Профиль — отдельный шаблон, а не наследник base.html.
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("profiles:detail", args=[self.other.pk])
        )
        self.assert_footer(response)
        own = self.client.get(reverse("profiles:self"), follow=True)
        self.assert_footer(own)

    def test_footer_styles_are_not_duplicated_in_catalog(self):
        # Правила подвала должны жить только в footer.css, иначе файлы расходятся.
        from pathlib import Path

        catalog_css = Path("static/css/catalog.css").read_text()
        footer_css = Path("static/css/footer.css").read_text()
        self.assertNotIn(".catalog-footer {", catalog_css)
        self.assertIn(".catalog-footer {", footer_css)
        self.assertIn("background: #141416", footer_css)
