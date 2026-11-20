from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from projects.models import Category, Project, ProjectRole


class RoleRequirementsDetailTests(TestCase):
    """Требования к роли раскрываются рядом с её названием."""

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            email="author@example.com", password="strong-pass-1"
        )
        self.category = Category.objects.create(name="Разработка")
        self.project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Учебный проект",
            description="Описание",
        )
        self.role = ProjectRole.objects.create(
            project=self.project,
            name="Backend-разработчик",
            capacity=2,
            description="Django, PostgreSQL и немного магии.",
        )
        self.client.force_login(self.author)

    def test_requirements_are_rendered_as_disclosure_next_to_name(self):
        response = self.client.get(
            reverse("projects:detail", args=[self.project.pk])
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("<details", html)
        detail_start = html.index("pg-role-details")
        summary_html = html[detail_start : html.index("</details>", detail_start)]
        self.assertIn(self.role.name, summary_html.split("</summary>")[0])
        self.assertIn("Django, PostgreSQL и немного магии.", summary_html)
        self.assertIn("Требования к роли", summary_html)

    def test_role_without_requirements_has_no_disclosure(self):
        self.role.description = ""
        self.role.save()
        response = self.client.get(
            reverse("projects:detail", args=[self.project.pk])
        )
        html = response.content.decode()
        self.assertNotIn("pg-role-details", html)
        self.assertIn(self.role.name, html)

    def test_required_skills_shown_inside_disclosure(self):
        from accounts.models import Skill

        skill, _ = Skill.objects.get_or_create(
            name="Django", defaults={"category": Skill.Category.HARD}
        )
        self.role.required_skills.add(skill)
        response = self.client.get(
            reverse("projects:detail", args=[self.project.pk])
        )
        self.assertContains(response, "pg-role-skills")


class RoleDescriptionFormTests(TestCase):
    """Автор может задать требования при создании проекта."""

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            email="creator@example.com", password="strong-pass-1"
        )
        self.category = Category.objects.create(name="Разработка")
        self.client.force_login(self.author)

    def payload(self, **overrides):
        data = {
            "title": "Новый проект",
            "description": "Описание проекта",
            "category_id": str(self.category.pk),
            "roles-TOTAL_FORMS": "1",
            "roles-INITIAL_FORMS": "0",
            "roles-MIN_NUM_FORMS": "1",
            "roles-MAX_NUM_FORMS": "1000",
            "roles-0-name": "Frontend-разработчик",
            "roles-0-capacity": "1",
            "roles-0-description": "HTML, CSS и немного HTMX.",
        }
        data.update(overrides)
        return data

    def test_description_is_saved_for_role(self):
        response = self.client.post(reverse("projects:create"), self.payload())
        project = Project.objects.get(title="Новый проект")
        self.assertEqual(response.status_code, 302)
        role = project.roles.get()
        self.assertEqual(role.description, "HTML, CSS и немного HTMX.")

    def test_description_is_optional(self):
        self.client.post(reverse("projects:create"), self.payload(**{"roles-0-description": ""}))
        role = Project.objects.get(title="Новый проект").roles.get()
        self.assertEqual(role.description, "")

    def test_create_form_exposes_description_field(self):
        response = self.client.get(reverse("projects:create"))
        self.assertContains(response, "roles-0-description")
