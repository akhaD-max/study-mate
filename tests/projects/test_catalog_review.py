"""Автоматизированная часть приёмки Sprint 6 на фактическом PostgreSQL.

Данные P01–P10/Q01–Q13 описаны в docs/sprint-6/catalog-test-cases.md.
Браузерные отказы сети и таймаут проверяются отдельно по review-demo.md;
этот модуль не подменяет проверку JavaScript обычным HTTP-ответом.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from applications.models import Application
from projects.models import Project, ProjectMember

from .review_data import seed_empty_pagination_catalog, seed_empty_review_catalog

TEST_PASSWORD = "Review-test-only-7N!"


class CatalogReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.projects = seed_empty_review_catalog(password=TEST_PASSWORD)

    def setUp(self):
        self.url = reverse("projects:catalog")

    def get(self, **params):
        return self.client.get(self.url, params)

    def keys(self, response):
        projects_by_id = {project.pk: key for key, project in self.projects.items()}
        return {projects_by_id[project.pk] for project in response.context["projects"]}

    def test_s6_01_title_and_description(self):
        response = self.get(q="Python")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.keys(response), {"P01", "P07"})
        self.assertEqual(response.context["project_count"], 2)
        self.assertContains(response, "User Research")

    def test_s6_02_missing_match_is_not_server_error(self):
        response = self.get(q="zzzz-no-match-8472")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.keys(response), set())
        self.assertContains(response, "Найдено проектов: 0")
        self.assertContains(response, "Проекты не найдены")
        self.assertContains(response, "Сбросить фильтры")

    def test_s6_03_empty_and_short_queries(self):
        for params in ({}, {"q": ""}, {"q": "   "}):
            with self.subTest(params=params):
                self.assertEqual(self.keys(self.get(**params)), {"P01", "P07", "P08"})
        response = self.get(q="Py")
        self.assertEqual(self.keys(response), {"P01", "P07"})

    def test_s6_04_case_and_edge_whitespace_on_postgresql(self):
        for text in ("Python", "python", " Python "):
            with self.subTest(text=text):
                response = self.get(q=text)
                self.assertEqual(self.keys(response), {"P01", "P07"})
                self.assertEqual(response.context["search_query"], text.strip())
        for text in ("РОБОТ", "робот"):
            with self.subTest(text=text):
                self.assertEqual(self.keys(self.get(q=text)), {"P08"})

    def test_s6_05_open_recruitment_and_pending_places(self):
        response = self.get()
        self.assertEqual(self.keys(response), {"P01", "P07", "P08"})
        self.assertEqual(Application.objects.filter(
            project=self.projects["P01"], status="pending",
        ).count(), 2)
        self.assertEqual(self.projects["P01"].roles.get().free_places, 1)

    def test_s6_06_filters_combine_with_and(self):
        for direction, expected in (
            ("development", {"P01"}), ("design", {"P07"}), ("science", set()),
        ):
            with self.subTest(direction=direction):
                self.assertEqual(self.keys(self.get(q="Python", direction=direction)), expected)
        for role in ("Backend", "backend"):
            with self.subTest(role=role):
                self.assertEqual(self.keys(self.get(
                    q="Python", direction="development", role=role,
                )), {"P01"})
        self.assertEqual(self.keys(self.get(
            q="Python", direction="design", role="Backend",
        )), set())
        response = self.get(role="Missing")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.keys(response), set())

    def test_s6_07_disable_recruitment_filter(self):
        self.assertEqual(self.keys(self.get(q="Python")), {"P01", "P07"})
        response = self.get(q="Python", open_only="false")
        self.assertEqual(self.keys(response), {
            "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P09", "P10",
        })
        self.assertEqual(response.context["project_count"], 9)
        self.assertContains(response, "Набор закрыт")
        self.assertEqual(self.keys(self.get(q="Python", open_only="true")), {"P01", "P07"})

    def test_s6_08_reset_link_restores_server_defaults(self):
        filtered = self.get(
            q="Python", direction="development", role="Backend",
            open_only="false", sort="oldest", page=2,
        )
        self.assertContains(filtered, 'href="/projects/"')
        response = self.client.get(reverse("projects:catalog"))
        self.assertEqual(response.context["search_query"], "")
        self.assertEqual(response.context["selected_direction"], "")
        self.assertEqual(response.context["selected_role"], "")
        self.assertTrue(response.context["open_only"])
        self.assertEqual(response.context["sort"], "newest")
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(self.keys(response), {"P01", "P07", "P08"})

    def test_s6_09_validation_boundaries_and_unknown_parameters(self):
        invalid = [
            ({"open_only": "maybe"}, "open_only"),
            ({"open_only": ""}, "open_only"),
            ({"open_only": "True"}, "open_only"),
            ({"q": "x" * 201}, "q"),
            ({"q": " " + "x" * 201 + " "}, "q"),
            ({"role": "x" * 101}, "role"),
            ({"direction": "bad!slug"}, "direction"),
            ({"direction": "x" * 101}, "direction"),
            *[({name: ["a", "a"]}, name) for name in
              ("q", "direction", "role", "open_only", "sort", "page")],
        ]
        for params, field in invalid:
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(params=params, headers=headers):
                    response = self.client.get(self.url, params, **headers)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.context["filter_errors"])
                    self.assertEqual(list(response.context["projects"]), [])
                    self.assertNotContains(response, '<article class="catalog-card"', status_code=400)
                    if headers:
                        self.assertContains(response, 'id="catalog-content"', status_code=400)
                        self.assertNotContains(response, "<!doctype html>", status_code=400)
        for params in ({"q": "x" * 200}, {"q": " " + "x" * 200 + " "}, {"role": "x" * 100}):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 200)
        response = self.get(direction="unknown-direction-8472")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.keys(response), set())
        response = self.get(sort="invalid")
        self.assertEqual(response.context["sort"], "newest")
        self.assertEqual(self.keys(self.get(unknown="ignored", search="not-an-alias")),
                         {"P01", "P07", "P08"})
        response = self.get(q='<script>alert("x")</script>')
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    @override_settings(DEBUG=False)
    def test_s6_10_server_error_is_html_not_empty_result(self):
        client = Client(raise_request_exception=False)
        with patch("projects.views.catalog_projects", side_effect=RuntimeError("QA fault")):
            response = client.get(self.url)
        self.assertEqual(response.status_code, 500)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertNotContains(response, "Найдено проектов: 0", status_code=500)

    def test_r01_stable_sorts_and_page_fallbacks(self):
        expected = {
            "newest": ["P08", "P07", "P01"],
            "oldest": ["P01", "P07", "P08"],
            "members": ["P01", "P08", "P07"],
            "fewer_members": ["P08", "P07", "P01"],
        }
        for sort, keys in expected.items():
            with self.subTest(sort=sort):
                self.assertEqual(list(self.keys_in_order(self.get(sort=sort))), keys)
        for page, number in (("abc", 1), ("", 1), (0, 1), (-1, 1), (999, 1)):
            with self.subTest(page=page):
                self.assertEqual(self.get(page=page).context["page_obj"].number, number)

    def keys_in_order(self, response):
        by_id = {project.pk: key for key, project in self.projects.items()}
        return [by_id[project.pk] for project in response.context["projects"]]

    def test_r02_full_fragment_history_and_vary(self):
        params = {"q": "Python", "direction": "design", "open_only": "false", "sort": "oldest"}
        full = self.get(**params)
        fragment = self.client.get(self.url, params, HTTP_HX_REQUEST="true")
        restored = self.client.get(self.url, params, HTTP_HX_REQUEST="true",
                                   HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        for response in (full, fragment, restored):
            self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
            for name in ("HX-Request", "HX-History-Restore-Request"):
                self.assertIn(name, response.headers["Vary"])
        for response in (full, restored):
            self.assertContains(response, "<!doctype html>")
        self.assertNotContains(fragment, "<!doctype html>")
        self.assertContains(fragment, 'id="catalog-content"')
        for response in (full, fragment, restored):
            self.assertEqual(response.context["project_count"], 1)
            self.assertEqual(self.keys(response), {"P07"})

    def test_r03_application_lifecycle_updates_open_recruitment(self):
        project = self.projects["P01"]
        role = project.roles.get()
        student = get_user_model().objects.get(email="review-student4@studymate.local")
        author = project.author
        self.client.force_login(student)
        response = self.client.post(reverse("applications:submit", args=[project.pk]), {
            "projectRoleId": str(role.pk), "comment": "Приёмка жизненного цикла",
        })
        self.assertRedirects(response, reverse("applications:mine"))
        application = Application.objects.get(project=project, user=student)
        self.assertEqual(application.status, "pending")
        self.assertIn("P01", self.keys(self.get(q="Python")))
        self.client.force_login(author)
        self.client.post(reverse("applications:accept", args=[application.pk]))
        application.refresh_from_db()
        self.assertEqual(application.status, "accepted")
        self.assertEqual(role.free_places, 0)
        self.assertNotIn("P01", self.keys(self.get(q="Python")))
        self.client.force_login(student)
        self.client.post(reverse("applications:leave", args=[project.pk]))
        self.assertFalse(ProjectMember.objects.filter(project=project, user=student).exists())
        self.assertIn("P01", self.keys(self.get(q="Python")))

    def test_r04_access_csrf_and_methods_do_not_change_catalog(self):
        before = Project.objects.count()
        detail = reverse("projects:detail", args=[self.projects["P01"].pk])
        self.assertRedirects(self.client.get(detail), f"{reverse('accounts:login')}?next={detail}")
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(self.url, {}).status_code, 403)
        strict.get(reverse("accounts:login"))
        token = strict.cookies["csrftoken"].value
        self.assertEqual(strict.post(self.url, {"csrfmiddlewaretoken": token}).status_code, 405)
        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(strict, method)(self.url, HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 405)
        for method in ("head", "options"):
            response = getattr(strict, method)(self.url)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(response.headers["Allow"], "GET")
        student = get_user_model().objects.get(email="review-student4@studymate.local")
        strict.force_login(student)
        application = Application.objects.filter(project=self.projects["P01"]).first()
        count = Application.objects.count()
        self.assertEqual(strict.post(reverse("applications:withdraw", args=[application.pk])).status_code, 403)
        self.assertEqual(Application.objects.count(), count)
        self.assertEqual(Project.objects.count(), before)


class CatalogPaginationReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.projects = seed_empty_pagination_catalog(password=TEST_PASSWORD)

    def test_r01_thirteen_projects_have_no_loss_or_duplicates(self):
        url = reverse("projects:catalog")
        first = self.client.get(url, {"q": "Python", "role": "Backend", "sort": "newest"})
        second = self.client.get(url, {"q": "Python", "role": "Backend", "sort": "newest", "page": 2})
        self.assertEqual(first.context["project_count"], 13)
        self.assertEqual(len(first.context["projects"]), 12)
        self.assertEqual(len(second.context["projects"]), 1)
        self.assertEqual([p.title for p in first.context["projects"]],
                         [f"Q{number:02d} Python" for number in range(13, 1, -1)])
        self.assertEqual(second.context["projects"][0].title, "Q01 Python")
        self.assertContains(first, "role=Backend")
        self.assertContains(first, "page=2")
        self.assertNotContains(first, 'name="page"')
        for page in (0, -1, 999):
            response = self.client.get(url, {"page": page})
            self.assertEqual(response.context["page_obj"].number, 2)
