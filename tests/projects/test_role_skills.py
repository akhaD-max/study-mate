from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Skill
from applications.models import Application
from projects.models import Category, Project, ProjectRole


class EditRoleSkillsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.author = users.create_user(email="skills-author@example.com")
        cls.candidate = users.create_user(email="skills-candidate@example.com")
        category = Category.objects.create(name="Проектирование")
        cls.project = Project.objects.create(
            author=cls.author, category=category, title="Проект с навыками",
        )
        cls.other_project = Project.objects.create(
            author=cls.author, category=category, title="Соседний проект",
        )
        cls.role = ProjectRole.objects.create(project=cls.project, name="Backend", capacity=2)
        cls.other_role = ProjectRole.objects.create(
            project=cls.project, name="Frontend", capacity=1,
        )
        cls.active = Skill.objects.create(name="Active role test", category=Skill.Category.SOFT)
        cls.retired = Skill.objects.create(
            name="Retired role test", category=Skill.Category.HARD, is_active=False,
        )
        cls.unavailable = Skill.objects.create(
            name="Unavailable role test", category=Skill.Category.HARD, is_active=False,
        )
        cls.role.required_skills.add(cls.retired)
        cls.other_role.required_skills.add(cls.active)
        cls.application = Application.objects.create(
            user=cls.candidate, project=cls.project, role=cls.role,
        )

    def setUp(self):
        self.client.force_login(self.author)
        self.url = reverse("projects:edit_role_skills", args=[self.project.pk, self.role.pk])

    def test_author_can_preserve_retired_skills_and_clear_requirements(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Retired role test (Неактивен)")
        self.assertEqual(response.context["form"]["required_skills"].value(), [str(self.retired.pk)])
        self.assertNotContains(response, "Unavailable role test")

        detail_url = reverse("projects:detail", args=[self.project.pk])
        response = self.client.post(self.url, {
            "required_skills": [str(self.retired.pk), str(self.active.pk)],
        })
        self.assertRedirects(response, detail_url)
        self.assertCountEqual(self.role.required_skills.all(), [self.retired, self.active])

        self.assertRedirects(self.client.post(self.url), detail_url)
        self.assertFalse(self.role.required_skills.exists())
        self.assertEqual(list(self.other_role.required_skills.all()), [self.active])
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.PENDING)
        self.role.refresh_from_db()
        self.assertEqual(self.role.capacity, 2)

    def test_invalid_skill_does_not_change_requirements(self):
        response = self.client.post(self.url, {
            "required_skills": [str(self.active.pk), str(self.unavailable.pk)],
        })
        form = response.context["form"]
        self.assertIn(str(self.active.pk), form["required_skills"].value())
        self.assertIn("required_skills", form.errors)
        self.assertEqual(list(self.role.required_skills.all()), [self.retired])

    def test_requires_owner_and_role_in_project(self):
        wrong_project_url = reverse(
            "projects:edit_role_skills", args=[self.other_project.pk, self.role.pk],
        )
        self.assertEqual(self.client.get(wrong_project_url).status_code, 404)
        self.assertEqual(self.client.post(wrong_project_url).status_code, 404)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.client.force_login(self.candidate)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(list(self.role.required_skills.all()), [self.retired])

    def test_requires_login_and_csrf(self):
        response = Client().get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        self.assertEqual(client.post(self.url).status_code, 403)
