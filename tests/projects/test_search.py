"""Поведение поиска на PostgreSQL, включая реальные места в выбранной роли."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from applications.models import Application
from projects.models import Category, Project, ProjectMember, ProjectRole


class ProjectSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = get_user_model().objects.create_user("search-author@example.com", "Password!1")
        cls.student = get_user_model().objects.create_user("search-student@example.com", "Password!1")
        cls.science = Category.objects.create(name="Наука", slug="science")
        cls.design = Category.objects.create(name="Дизайн", slug="design")
        cls.project = Project.objects.create(
            author=cls.author, category=cls.science, title="Python Робот", description="Чат-бот 100%_ready",
        )
        cls.backend = ProjectRole.objects.create(project=cls.project, name="Backend", capacity=1)
        cls.designer = ProjectRole.objects.create(project=cls.project, name="Designer", capacity=2)
        cls.closed = Project.objects.create(
            author=cls.author, category=cls.design, title="Python архив", status="completed",
        )
        ProjectRole.objects.create(project=cls.closed, name="backend", capacity=1)
        cls.no_roles = Project.objects.create(author=cls.author, category=cls.design, title="Без ролей")

    def search(self, **params):
        return self.client.get(reverse("projects:catalog"), params)

    def ids(self, response):
        return [project.pk for project in response.context["projects"]]

    def test_text_category_role_and_availability_are_combined(self):
        for text in ["python", " Python ", "РОБОТ", "чат", "р"]:
            with self.subTest(text=text):
                response = self.search(q=text, direction="science", role="BACKEND")
                self.assertEqual(self.ids(response), [self.project.pk])
        self.assertEqual(self.ids(self.search(q="Python", direction="design")), [])
        self.assertEqual(self.ids(self.search(role="Missing")), [])

    def test_all_statuses_and_projects_without_roles_when_open_filter_disabled(self):
        self.assertCountEqual(self.ids(self.search(open_only="false")), [self.project.pk, self.closed.pk, self.no_roles.pk])
        response = self.search(open_only="false", role="Backend", q="Python")
        self.assertCountEqual(self.ids(response), [self.project.pk, self.closed.pk])
        self.assertContains(response, "Набор закрыт")

    def test_selected_role_must_have_its_own_free_place(self):
        ProjectMember.objects.create(project=self.project, role=self.backend, user=self.student)
        self.assertEqual(self.ids(self.search(role="Backend")), [])
        # Другая роль ещё свободна: без фильтра должности проект доступен.
        self.assertEqual(self.ids(self.search()), [self.project.pk])
        self.assertEqual(self.ids(self.search(role="Designer")), [self.project.pk])
        self.assertIn(self.project.pk, self.ids(self.search(role="Backend", open_only="false")))

    def test_closed_free_role_cannot_compensate_for_full_open_role(self):
        ProjectMember.objects.create(project=self.project, role=self.backend, user=self.student)
        self.designer.is_open = False
        self.designer.save(update_fields=["is_open"])
        self.assertEqual(self.ids(self.search()), [])

    def test_pending_application_does_not_reserve_place(self):
        Application.objects.create(project=self.project, role=self.backend, user=self.student)
        self.assertEqual(self.ids(self.search(role="Backend")), [self.project.pk])

    def test_role_choices_come_from_database_and_ignore_case_duplicates(self):
        names = list(self.search().context["role_names"])
        self.assertCountEqual([name.lower() for name in names], ["backend", "designer"])
        ProjectRole.objects.create(project=self.no_roles, name="Аналитик", capacity=1)
        self.assertIn("Аналитик", self.search().context["role_names"])

    def test_literal_percent_underscore_and_html_are_safe(self):
        self.assertEqual(self.ids(self.search(q="%_")), [self.project.pk])
        self.assertEqual(self.ids(self.search(q="%x")), [])
        response = self.search(q='<script>alert("x")</script>')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_invalid_parameters_return_errors_without_results(self):
        for params, field in [
            ({"q": "x" * 201}, "q"), ({"open_only": ""}, "open_only"),
            ({"open_only": "1"}, "open_only"), ({"direction": "bad/slug"}, "direction"),
            ({"role": "x" * 101}, "role"), ({"q": ["a", "a"]}, "q"),
            ({"page": ["1", "2"]}, "page"), ({"role": ["Backend", "Designer"]}, "role"),
        ]:
            with self.subTest(params=params):
                response = self.search(**params)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.context["filter_errors"])
                self.assertEqual(self.ids(response), [])
                self.assertNotContains(response, '<article class="catalog-card"', status_code=400)

    def test_valid_unknown_values_are_preserved_in_empty_form(self):
        response = self.search(role="Исчезнувшая роль", direction="removed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), [])
        self.assertContains(response, 'value="Исчезнувшая роль" selected')
        self.assertContains(response, 'value="removed" selected')

    def test_pagination_keeps_all_conditions_and_does_not_duplicate_cards(self):
        for number in range(13):
            project = Project.objects.create(author=self.author, category=self.science, title=f"Python {number}")
            ProjectRole.objects.create(project=project, name="Backend", capacity=1)
        response = self.search(q="Python", role="Backend", direction="science", open_only="false", sort="oldest")
        self.assertEqual(response.context["project_count"], 14)
        self.assertEqual(len(self.ids(response)), 12)
        self.assertContains(response, "role=Backend")
        self.assertContains(response, "open_only=false")
        second = self.search(q="Python", role="Backend", direction="science", open_only="false", sort="oldest", page=2)
        self.assertEqual(len(self.ids(second)), 2)
        self.assertFalse(set(self.ids(response)) & set(self.ids(second)))

    def test_htmx_validation_and_history_restore(self):
        url = reverse("projects:catalog")
        response = self.client.get(url, {"q": "x" * 201}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="catalog-content"', status_code=400)
        self.assertNotContains(response, "<!doctype html>", status_code=400)
        restored = self.client.get(url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(restored, "<!doctype html>")
        self.assertIn("HX-History-Restore-Request", restored.headers["Vary"])

    def test_home_login_registration_and_detail_paths(self):
        self.assertRedirects(self.client.get(reverse("main:home")), reverse("projects:catalog"))
        self.assertRedirects(self.client.post(reverse("accounts:login"), {
            "username": self.student.email, "password": "Password!1",
        }), reverse("main:home"), target_status_code=302)
        self.client.logout()
        self.assertRedirects(self.client.post(reverse("accounts:register"), {
            "email": "search-new@example.com", "password": "Password!1",
        }), reverse("main:home"), target_status_code=302)
        self.client.logout()
        detail = reverse("projects:detail", args=[self.project.pk])
        self.assertRedirects(self.client.get(detail), f"{reverse('accounts:login')}?next={detail}")

    def test_post_does_not_run_search(self):
        self.assertEqual(self.client.post(reverse("projects:catalog")).status_code, 405)
