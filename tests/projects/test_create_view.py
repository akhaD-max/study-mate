from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from projects.models import Category, Project


class CreateProjectViewTests(TestCase):
    """Сценарий создания проекта: роли добавляются без перезагрузки страницы."""

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            email="author@example.com", password="strong-pass-1"
        )
        self.category = Category.objects.create(name="Разработка")
        self.url = reverse("projects:create")
        self.client.force_login(self.author)

    def payload(self, **overrides):
        data = {
            "title": "Учебный проект",
            "description": "Описание проекта",
            "category_id": str(self.category.pk),
            "roles-TOTAL_FORMS": "1",
            "roles-INITIAL_FORMS": "0",
            "roles-MIN_NUM_FORMS": "1",
            "roles-MAX_NUM_FORMS": "1000",
            "roles-0-name": "Backend",
            "roles-0-capacity": "1",
        }
        data.update(overrides)
        return data

    def test_add_role_with_htmx_returns_only_formset(self):
        response = self.client.post(
            self.url, self.payload(action="add_role"), HTTP_HX_REQUEST="true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="role-formset"')
        self.assertNotContains(response, "<!doctype html>")
        self.assertNotContains(response, 'name="title"')
        self.assertNotContains(response, 'name="description"')
        self.assertContains(response, 'name="roles-1-name"')
        self.assertContains(response, "Backend")
        self.assertContains(response, "value=\"2\"")
        self.assertFalse(Project.objects.exists())

    def test_add_role_keeps_filled_fields_and_appends_empty_role(self):
        response = self.client.post(
            self.url, self.payload(action="add_role"), HTTP_HX_REQUEST="true"
        )
        html = response.content.decode()

        self.assertEqual(html.count('<fieldset class="role-fields">'), 2)
        self.assertIn('value="Backend"', html)
        self.assertIn('value="1"', html)
        self.assertIn("roles-1-name", html)

    def test_add_role_without_htmx_returns_full_page(self):
        response = self.client.post(self.url, self.payload(action="add_role"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<!doctype html>")
        self.assertContains(response, 'name="roles-1-name"')
        self.assertFalse(Project.objects.exists())

    def test_project_is_created_with_all_roles_added_by_htmx(self):
        data = self.payload(
            action=None,
            **{
                "roles-TOTAL_FORMS": "2",
                "roles-1-name": "Дизайнер",
                "roles-1-capacity": "3",
            },
        )
        data.pop("action")
        response = self.client.post(self.url, data)

        project = Project.objects.get()
        self.assertRedirects(response, reverse("projects:detail", args=[project.pk]))
        self.assertEqual(
            list(project.roles.values_list("name", "capacity")),
            [("Backend", 1), ("Дизайнер", 3)],
        )

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(
            self.url, self.payload(action="add_role"), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.headers["Location"])
