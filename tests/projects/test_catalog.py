from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from projects.models import Category, Project, ProjectRole


class CatalogRenderingTests(SimpleTestCase):
    def setUp(self):
        self.queryset = MagicMock()
        for method in ("select_related", "annotate", "prefetch_related", "filter"):
            getattr(self.queryset, method).return_value = self.queryset
        self.queryset.order_by.return_value = []
        project_patch = patch(
            "main.views.Project.objects.filter", return_value=self.queryset
        )
        category_patch = patch("main.views.Category.objects.all", return_value=[])
        project_patch.start()
        category_patch.start()
        self.addCleanup(project_patch.stop)
        self.addCleanup(category_patch.stop)
        self.url = reverse("main:catalog")

    def test_empty_database_has_no_demo_cards(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Пока нет проектов")
        self.assertContains(response, "Проектов: 0")
        self.assertContains(response, "css/catalog.css")
        self.assertNotContains(response, '<article class="catalog-card')
        self.assertNotContains(response, "Личный кабинет")
        self.assertNotContains(response, "Не обязательно")
        self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_htmx_fragment_and_history_restore(self):
        response = self.client.get(self.url, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="catalog-content"')
        self.assertNotContains(response, "<!doctype html>")
        self.assertIn("HX-Request", response.headers["Vary"])
        restored = self.client.get(
            self.url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"
        )
        self.assertContains(restored, "<!doctype html>")

    def test_render_real_model_attributes_and_escape_title(self):
        author = get_user_model()(email="author@example.com", full_name="Автор")
        category = Category(name="Наука", slug="science")
        project = Project(title="Проект <script>", author=author, category=category)
        role = ProjectRole(name="Python", capacity=3, project=project)
        role._occupied_count = 1
        project.catalog_roles = [role]
        project.member_count = 1
        self.queryset.order_by.return_value = [project]
        response = self.client.get(self.url)
        self.assertContains(response, "Проект &lt;script&gt;")
        self.assertContains(response, "Автор · Наука")
        self.assertContains(response, "Python — свободных мест: 2")
        self.assertContains(response, "/ 01")
        self.assertNotContains(response, "Проект <script>")

    def test_filters_and_invalid_sort(self):
        response = self.client.get(
            self.url, {"direction": "science", "q": "робот", "sort": "invalid"}
        )
        self.queryset.filter.assert_any_call(category__slug="science")
        self.queryset.order_by.assert_called_once_with("-created_at", "pk")
        self.assertContains(response, "Проекты не найдены")
        self.assertContains(response, "Сбросить фильтры")
        self.assertContains(response, 'value="робот"')

    def test_sort_modes_use_database_ordering(self):
        for sort, expected in (
            ("newest", ("-created_at", "pk")),
            ("oldest", ("created_at", "pk")),
            ("members", ("-member_count", "-created_at", "pk")),
            ("fewer_members", ("member_count", "-created_at", "pk")),
        ):
            with self.subTest(sort=sort):
                self.queryset.order_by.reset_mock()
                response = self.client.get(self.url, {"sort": sort})
                self.assertEqual(response.status_code, 200)
                self.queryset.order_by.assert_called_once_with(*expected)

    def test_pagination_links_preserve_filters(self):
        author = get_user_model()(email="author@example.com")
        category = Category(name="Наука", slug="science")
        projects = []
        for index in range(13):
            project = Project(title=f"Проект {index}", author=author, category=category)
            project.catalog_roles = []
            project.member_count = 0
            projects.append(project)
        self.queryset.order_by.return_value = projects
        response = self.client.get(self.url, {"q": "Проект", "direction": "science"})
        self.assertContains(response, "Страница 1 из 2")
        self.assertContains(response, "direction=science")
        self.assertContains(response, "page=2")
        response = self.client.get(self.url, {"page": 2})
        self.assertContains(response, "/ 13")


class CatalogDatabaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = get_user_model().objects.create_user(
            "author@example.com", "Password!"
        )
        cls.category = Category.objects.create(name="Наука", slug="science")
        cls.other_category = Category.objects.create(name="Дизайн", slug="design")
        cls.project = Project.objects.create(
            author=cls.author,
            category=cls.category,
            title="Робот",
            description="Научная работа",
        )
        ProjectRole.objects.create(project=cls.project, name="Python", capacity=2)
        Project.objects.create(
            author=cls.author, category=cls.other_category, title="Макет"
        )
        Project.objects.create(
            author=cls.author,
            category=cls.category,
            title="Закрытый",
            status="completed",
        )

    def test_only_existing_open_projects_and_roles(self):
        response = self.client.get(reverse("main:catalog"))
        self.assertContains(response, "Робот")
        self.assertContains(response, "Макет")
        self.assertNotContains(response, "Закрытый")
        self.assertContains(response, "Python")
        self.assertEqual(response.context["project_count"], 2)

    def test_category_search_and_empty_result(self):
        url = reverse("main:catalog")
        response = self.client.get(url, {"direction": "science", "q": "РОБОТ"})
        self.assertEqual(response.context["project_count"], 1)
        self.assertContains(response, "Робот")
        self.assertNotContains(response, ">Макет<")
        response = self.client.get(url, {"direction": "design", "q": "робот"})
        self.assertEqual(response.context["project_count"], 0)
        self.assertContains(response, "Проекты не найдены")

    def test_empty_database(self):
        Project.objects.all().delete()
        response = self.client.get(reverse("main:catalog"))
        self.assertContains(response, "Пока нет проектов")
        self.assertNotContains(response, '<article class="catalog-card')

    def test_query_count_does_not_grow_with_cards(self):
        for index in range(5):
            Project.objects.create(
                title=f"Новый {index}", author=self.author, category=self.category
            )
        # Count + projects with joins + prefetched roles + categories.
        with self.assertNumQueries(4):
            self.client.get(reverse("main:catalog"))
