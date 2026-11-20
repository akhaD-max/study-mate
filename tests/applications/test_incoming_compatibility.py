from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Skill
from applications.models import Application
from applications.services import list_project_applications
from projects.models import Category, Project, ProjectRole
from projects.services import create_project


class IncomingCompatibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(email="owner@example.com")
        cls.candidate = User.objects.create_user(email="candidate@example.com", full_name="Кандидат")
        cls.other = User.objects.create_user(email="other@example.com")
        cls.category = Category.objects.create(name="Категория")
        cls.project = Project.objects.create(author=cls.owner, category=cls.category, title="Проект")
        cls.role = ProjectRole.objects.create(project=cls.project, name="Разработчик", capacity=1)
        cls.skills = [Skill.objects.create(name=f"Тестовый навык {i}", category="hard")
                      for i in range(1, 9)]
        cls.extra = Skill.objects.create(name="Дополнительный", category="soft")
        cls.application = Application.objects.create(
            project=cls.project, role=cls.role, user=cls.candidate, comment="Письмо <script>",
        )

    def setUp(self):
        self.client.force_login(self.owner)
        self.url = reverse("applications:incoming", args=[self.project.pk])

    def test_page_match_filters_refresh_and_permission(self):
        self.role.required_skills.set(self.skills[:4])
        self.candidate.skills.set(self.skills[:3] + [self.extra])
        response = self.client.get(self.url)
        self.assertContains(response, "75% · совпало 3 из 4 навыков")
        self.assertContains(response, "Не хватает")
        self.assertContains(response, "Дополнительные навыки")
        self.assertContains(response, "Письмо &lt;script&gt;")
        self.assertContains(response, "На рассмотрении · 1")
        self.assertNotContains(self.client.get(self.url, {"status": "accepted"}), "Кандидат")
        self.candidate.skills.add(self.skills[3])
        self.assertContains(self.client.get(self.url), "100% · совпало 4 из 4 навыков")
        self.role.required_skills.set(self.skills)
        self.candidate.skills.set(self.skills[:1])
        self.assertContains(self.client.get(self.url), "13% · совпало 1 из 8 навыков")
        self.application.status = Application.Status.REJECTED
        self.application.save()
        self.assertContains(self.client.get(self.url), "По текущим навыкам и требованиям роли")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_empty_skills_and_rerender_on_review_error(self):
        self.assertContains(self.client.get(self.url), "У роли не заданы требуемые навыки")
        self.role.required_skills.add(self.skills[0])
        page = self.client.get(self.url)
        self.assertContains(page, "0% · совпало 0 из 1 навыков")
        self.assertContains(page, "Кандидат пока не указал навыки")
        self.role.is_open = False
        self.role.save()
        response = self.client.post(reverse("applications:accept", args=[self.application.pk]))
        self.assertContains(response, "0% · совпало 0 из 1 навыков")
        self.assertContains(response, "Роль закрыта")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.PENDING)

    def test_requirements_are_role_specific_and_edit_preserves_application(self):
        other_role = ProjectRole.objects.create(project=self.project, name="Дизайнер", capacity=2)
        other_role.required_skills.add(self.skills[1])
        self.role.required_skills.add(self.skills[0])
        self.candidate.skills.add(self.skills[0])
        self.assertContains(self.client.get(self.url), "100% · совпало 1 из 1 навыков")
        url = reverse("projects:edit_role_skills", args=[self.project.pk, self.role.pk])
        self.assertEqual(self.client.post(url, {"required_skills": [str(self.skills[1].pk)]}).status_code, 302)
        self.assertContains(self.client.get(self.url), "0% · совпало 0 из 1 навыков")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.PENDING)
        self.assertEqual(other_role.required_skills.get(), self.skills[1])
        self.assertEqual(self.role.capacity, 1)
        foreign_project = Project.objects.create(author=self.owner, category=self.category, title="Другой")
        foreign_url = reverse("projects:edit_role_skills", args=[foreign_project.pk, self.role.pk])
        self.assertEqual(self.client.get(foreign_url).status_code, 404)

    def test_prefetch_queries_do_not_grow_per_application(self):
        self.role.required_skills.add(self.skills[0])
        with self.assertNumQueries(4):
            project, applications = list_project_applications(user=self.owner, project_id=self.project.pk)
            self.assertEqual(applications[0].skill_match["required_count"], 1)
        Application.objects.create(project=project, role=self.role, user=self.other)
        with self.assertNumQueries(4):
            _, applications = list_project_applications(user=self.owner, project_id=self.project.pk)
            self.assertEqual(len(applications), 2)

    def test_role_edit_validation_permission_and_csrf(self):
        inactive = self.skills[0]
        inactive.is_active = False
        inactive.save()
        self.role.required_skills.add(inactive)
        url = reverse("projects:edit_role_skills", args=[self.project.pk, self.role.pk])
        self.assertContains(self.client.get(url), "Неактивен")
        self.assertEqual(self.client.post(url, {"required_skills": [str(inactive.pk)]}).status_code, 302)
        for invalid in (str(uuid4()), "not-a-uuid", ""):
            response = self.client.post(url, {"required_skills": [invalid]})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.client.post(url, {})
        self.assertFalse(self.role.required_skills.exists())
        response = self.client.post(url, {"required_skills": [str(inactive.pk)]})
        self.assertTrue(response.context["form"].errors)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(url, {}).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_creation_saves_separate_roles_and_rejects_invalid_skills(self):
        project = create_project(author=self.owner, title="Второй проект", description="Описание",
                                 category_id=self.category.pk, roles=[
                                     {"name": "A", "capacity": 1, "required_skills": [self.skills[0].pk]},
                                     {"name": "B", "capacity": 1, "required_skills": [self.skills[1].pk]},
                                 ])
        roles = list(project.roles.all())
        self.assertEqual(list(roles[0].required_skills.all()), [self.skills[0]])
        self.assertEqual(list(roles[1].required_skills.all()), [self.skills[1]])
        with self.assertRaises(ValidationError):
            create_project(author=self.owner, title="Ошибка", description="Описание",
                           category_id=self.category.pk, roles=[
                               {"name": "A", "capacity": 1, "required_skills": [uuid4()]},
                           ])
        self.assertFalse(Project.objects.filter(title="Ошибка").exists())

    def test_create_form_preserves_skill_selection_and_validates_each_role(self):
        url = reverse("projects:create")
        data = {
            "title": "Новый проект", "description": "Описание", "category_id": str(self.category.pk),
            "roles-TOTAL_FORMS": "1", "roles-INITIAL_FORMS": "0",
            "roles-0-name": "Backend", "roles-0-capacity": "1",
            "roles-0-required_skills": [str(self.skills[0].pk)],
        }
        response = self.client.post(url, data | {"action": "add_role"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'name="roles-0-required_skills"')
        self.assertContains(response, 'checked')
        self.assertFalse(Project.objects.filter(title="Новый проект").exists())
        response = self.client.post(url, data | {"roles-0-required_skills": [str(uuid4())]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["role_formset"].errors[0])
        self.assertFalse(Project.objects.filter(title="Новый проект").exists())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        role = Project.objects.get(title="Новый проект").roles.get()
        self.assertEqual(list(role.required_skills.all()), [self.skills[0]])

    def test_profile_uses_standard_footer(self):
        for url in (reverse("profiles:self"), reverse("profiles:edit")):
            page = self.client.get(url)
            self.assertContains(page, 'class="catalog-footer"')
            self.assertContains(page, "сделаем вместе")
            self.assertContains(page, "Найди свою команду")
            self.assertNotContains(page, 'class="profile-footer"')
