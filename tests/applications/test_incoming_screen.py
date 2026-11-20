"""Экран «Входящие заявки» руководителя: табы статусов и общий подвал.

Проверяет макет из Sprint 8: счётчики в табах, фильтр по `?status=`,
сохранение порядка «новые сначала» и блок совместимости внутри карточки.
Отдельно проверяется, что подвал одинаков на всех страницах приложения.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Skill
from applications.models import Application
from applications.services import submit_application
from projects.models import Category, Project, ProjectRole

FOOTER = (
    '<footer class="catalog-footer"><div><strong>studymate</strong> / сделаем вместе'
    "</div><span>Учебный проект · Ростелеком</span></footer>"
)


class IncomingScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.author = users.create_user("screen-owner@example.com", "Password!1")
        cls.pending_user = users.create_user("pending@example.com", "Password!1")
        cls.accepted_user = users.create_user("accepted@example.com", "Password!1")
        cls.rejected_user = users.create_user("rejected@example.com", "Password!1")
        cls.category = Category.objects.create(name="Наука", slug="science")
        cls.project = Project.objects.create(
            author=cls.author, category=cls.category, title="Хакатон связи",
        )
        cls.role = ProjectRole.objects.create(project=cls.project, name="ML-инженер", capacity=3)
        cls.role.required_skills.set([Skill.objects.get(name="Python")])
        cls.applications = {}
        for status, user in (
            (Application.Status.PENDING, cls.pending_user),
            (Application.Status.ACCEPTED, cls.accepted_user),
            (Application.Status.REJECTED, cls.rejected_user),
        ):
            application = submit_application(
                user=user, project_id=cls.project.pk, role_id=cls.role.pk,
            )
            application.status = status
            application.save(update_fields=["status"])
            cls.applications[status] = application
        cls.url = reverse("applications:incoming", args=[cls.project.pk])

    def setUp(self):
        self.client.force_login(self.author)

    def test_status_tabs_show_counts_and_active_state(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Все")
        self.assertContains(response, "На рассмотрении")
        self.assertContains(response, "Приняты")
        self.assertContains(response, "Отклонены")
        self.assertContains(response, 'class="in-tab is-active" href="?status=all"')
        # Счётчики берутся из всех заявок проекта независимо от фильтра.
        for status, count in (("pending", 1), ("accepted", 1), ("rejected", 1)):
            self.assertContains(response, f'href="?status={status}"', count=1)
        self.assertEqual(response.context["counts"]["all"], 3)

    def test_status_filter_shows_only_matching_cards(self):
        for status in (
            Application.Status.PENDING,
            Application.Status.ACCEPTED,
            Application.Status.REJECTED,
        ):
            with self.subTest(status=status):
                response = self.client.get(self.url, {"status": status})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["active_status"], status)
                shown = list(response.context["applications"])
                self.assertEqual([item.status for item in shown], [status])
                self.assertContains(response, f'class="in-tab is-active" href="?status={status}"')
                # Сквозные счётчики не меняются от выбранного таба.
                self.assertEqual(response.context["counts"]["all"], 3)

    def test_unknown_status_shows_all_applications(self):
        response = self.client.get(self.url, {"status": "archived"})
        self.assertEqual(response.context["active_status"], "all")
        self.assertEqual(len(response.context["applications"]), 3)

    def test_order_stays_newest_first(self):
        response = self.client.get(self.url, {"status": "all"})
        shown = [item.created_at for item in response.context["applications"]]
        self.assertEqual(shown, sorted(shown, reverse=True))

    def test_empty_filter_state_offers_way_back(self):
        self.applications[Application.Status.ACCEPTED].delete()
        response = self.client.get(self.url, {"status": "accepted"})
        self.assertContains(response, "Здесь пусто")
        self.assertContains(response, 'href="?status=all"')
        self.assertContains(response, "Показать все заявки")

    def test_no_applications_state(self):
        self.project.applications.all().delete()
        response = self.client.get(self.url)
        self.assertContains(response, "Пока нет заявок")
        self.assertNotContains(response, 'class="in-card"')

    def test_card_keeps_match_block_and_actions(self):
        response = self.client.get(self.url, {"status": "pending"})
        self.assertContains(response, "Совместимость по навыкам")
        self.assertContains(response, "Принять")
        self.assertContains(response, "Отклонить")
        accepted = self.client.get(self.url, {"status": "accepted"})
        self.assertContains(accepted, "В команде")
        self.assertNotContains(accepted, "Принять")
        rejected = self.client.get(self.url, {"status": "rejected"})
        self.assertContains(rejected, "Архив заявок")
        self.assertContains(rejected, "Профиль кандидата")

    def test_screen_keeps_parent_stylesheets(self):
        response = self.client.get(self.url)
        for stylesheet in ("css/catalog.css", "css/workflow.css", "css/pages.css", "css/incoming.css"):
            self.assertContains(response, stylesheet)

    def test_footer_is_the_same_on_all_pages(self):
        pages = [
            self.url,
            reverse("projects:catalog"),
            reverse("applications:mine"),
            reverse("projects:mine"),
            reverse("projects:detail", args=[self.project.pk]),
        ]
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, FOOTER, count=1)
        # /profile/ перенаправляет на профиль текущего пользователя.
        own_profile = self.client.get(reverse("profiles:self"), follow=True)
        self.assertEqual(own_profile.status_code, 200)
        self.assertContains(own_profile, FOOTER, count=1)

    def test_guest_auth_page_uses_same_footer(self):
        self.client.logout()
        for page in (reverse("accounts:login"), reverse("accounts:register")):
            with self.subTest(page=page):
                self.assertContains(self.client.get(page), FOOTER, count=1)
