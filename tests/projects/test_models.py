import uuid

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, RestrictedError
from django.test import TestCase
from django.urls import reverse

from projects.models import Category, Project, ProjectMember, ProjectRole

User = get_user_model()

PASSWORD = "test-pass-12345"


def make_user(email: str, password: str = PASSWORD, *, superuser: bool = False):
    kwargs = {"email": email, "password": password}
    if User.USERNAME_FIELD != "email":
        kwargs[User.USERNAME_FIELD] = email
    if superuser:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class ProjectModelsTests(TestCase):
    def setUp(self):
        self.author = make_user("author@example.com")
        self.student_one = make_user("student1@example.com")
        self.student_two = make_user("student2@example.com")
        self.category = Category.objects.create(
            name="Разработка",
            slug="development",
        )

    def test_create_project_with_roles_and_member(self):
        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Платформа учебных проектов",
            description="Веб-сервис для набора студентов в команды.",
        )
        backend_role = ProjectRole.objects.create(
            project=project,
            name="Backend-разработчик",
            description="Django и PostgreSQL",
            capacity=2,
        )
        frontend_role = ProjectRole.objects.create(
            project=project,
            name="Frontend-разработчик",
            capacity=1,
        )
        member = ProjectMember.objects.create(
            project=project,
            role=backend_role,
            user=self.student_one,
        )

        self.assertIsInstance(self.category.pk, uuid.UUID)
        self.assertIsInstance(project.pk, uuid.UUID)
        self.assertIsInstance(backend_role.pk, uuid.UUID)
        self.assertIsInstance(member.pk, uuid.UUID)
        self.assertEqual(project.status, Project.Status.OPEN)
        self.assertEqual(project.roles.count(), 2)
        self.assertEqual(project.memberships.count(), 1)
        self.assertEqual(backend_role.occupied_places, 1)
        self.assertEqual(backend_role.free_places, 1)
        self.assertEqual(frontend_role.occupied_places, 0)
        self.assertEqual(frontend_role.free_places, 1)
        self.assertTrue(backend_role.is_open)
        self.assertTrue(backend_role.is_available)

    def test_minimal_card_fields_without_mutable_counter_or_backlog_columns(self):
        role_fields = {f.name for f in ProjectRole._meta.concrete_fields}
        project_fields = {f.name for f in Project._meta.concrete_fields}

        self.assertEqual(
            role_fields,
            {
                "id",
                "project",
                "name",
                "description",
                "capacity",
                "is_open",
                "created_at",
            },
        )
        self.assertEqual(
            project_fields,
            {
                "id",
                "author",
                "category",
                "title",
                "description",
                "status",
                "created_at",
                "updated_at",
            },
        )

    def test_occupancy_and_availability_derived_from_membership(self):
        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Аналитика данных",
        )
        role = ProjectRole.objects.create(
            project=project,
            name="Data Analyst",
            capacity=2,
        )

        self.assertEqual(role.occupied_places, 0)
        self.assertEqual(role.free_places, 2)
        self.assertTrue(role.is_available)

        first = ProjectMember.objects.create(
            project=project,
            role=role,
            user=self.student_one,
        )
        self.assertEqual(role.occupied_places, 1)
        self.assertEqual(role.free_places, 1)
        self.assertTrue(role.is_available)

        second = ProjectMember.objects.create(
            project=project,
            role=role,
            user=self.student_two,
        )
        self.assertEqual(role.occupied_places, 2)
        self.assertEqual(role.free_places, 0)
        self.assertFalse(role.is_available)

        # Освобождение места сразу отражается в расчёте без ручного счётчика.
        second.delete()
        self.assertEqual(role.occupied_places, 1)
        self.assertEqual(role.free_places, 1)
        self.assertTrue(role.is_available)

        # Закрытие набора у роли блокирует отклик даже при наличии свободного места.
        role.is_open = False
        role.save()
        self.assertFalse(role.is_available)

        role.is_open = True
        role.save()
        project.status = Project.Status.IN_PROGRESS
        project.save()
        self.assertFalse(role.is_available)

        annotated = ProjectRole.objects.with_occupancy().get(pk=role.pk)
        self.assertEqual(annotated.occupied_places, 1)
        first.delete()
        annotated.refresh_from_db()
        self.assertEqual(annotated.occupied_places, 0)

    def test_role_capacity_must_be_strictly_positive_in_python_and_postgresql(self):
        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Чат-бот кафедры",
        )

        unsaved = ProjectRole(project=project, name="QA", capacity=0)
        with self.assertRaises(ValidationError):
            unsaved.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectRole.objects.create(project=project, name="QA", capacity=0)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectRole.objects.bulk_create(
                [ProjectRole(project=project, name="QA", capacity=0)]
            )

        valid_role = ProjectRole.objects.create(project=project, name="QA", capacity=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectRole.objects.filter(pk=valid_role.pk).update(capacity=0)

    def test_role_capacity_cannot_be_reduced_below_occupied_in_clean(self):
        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Мобильное приложение",
        )
        role = ProjectRole.objects.create(project=project, name="iOS", capacity=2)
        ProjectMember.objects.create(
            project=project,
            role=role,
            user=self.student_one,
        )
        ProjectMember.objects.create(
            project=project,
            role=role,
            user=self.student_two,
        )

        role.capacity = 1
        with self.assertRaises(ValidationError):
            role.full_clean()

    def test_unique_project_member_pair_in_postgresql(self):
        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Рекомендательная система",
        )
        backend = ProjectRole.objects.create(
            project=project,
            name="Backend",
            capacity=2,
        )
        ml = ProjectRole.objects.create(project=project, name="ML", capacity=2)
        ProjectMember.objects.create(
            project=project,
            role=backend,
            user=self.student_one,
        )

        # Повторное добавление в тот же проект запрещено даже на другую роль.
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMember.objects.create(
                project=project,
                role=ml,
                user=self.student_one,
            )

        # Участие того же студента в другом проекте разрешено.
        other_project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Второй учебный проект",
        )
        other_role = ProjectRole.objects.create(
            project=other_project,
            name="ML",
            capacity=1,
        )
        second_membership = ProjectMember.objects.create(
            project=other_project,
            role=other_role,
            user=self.student_one,
        )
        self.assertEqual(second_membership.project, other_project)

    def test_member_role_must_belong_to_project_in_clean_and_postgresql(self):
        project_one = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Проект А",
        )
        project_two = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Проект Б",
        )
        own_role = ProjectRole.objects.create(
            project=project_one,
            name="Backend",
            capacity=2,
        )
        foreign_role = ProjectRole.objects.create(
            project=project_two,
            name="Дизайнер",
            capacity=2,
        )

        invalid_member = ProjectMember(
            project=project_one,
            role=foreign_role,
            user=self.student_one,
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_member.full_clean()
        self.assertIn("role", ctx.exception.message_dict)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMember.objects.create(
                project=project_one,
                role=foreign_role,
                user=self.student_one,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMember.objects.bulk_create(
                [
                    ProjectMember(
                        project=project_one,
                        role=foreign_role,
                        user=self.student_one,
                    )
                ]
            )

        valid_member = ProjectMember.objects.create(
            project=project_one,
            role=own_role,
            user=self.student_one,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMember.objects.filter(pk=valid_member.pk).update(role=foreign_role)

    def test_category_project_and_deletion_constraints_in_postgresql(self):
        auto_slug_category = Category.objects.create(name="Дизайн интерфейсов")
        self.assertTrue(auto_slug_category.slug)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="разработка", slug="dev-duplicate")

        project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Уникальное название",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Project.objects.create(
                author=self.author,
                category=self.category,
                title="Уникальное название",
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Project.objects.filter(pk=project.pk).update(status="archived")

        occupied_role = ProjectRole.objects.create(
            project=project,
            name="Backend",
            capacity=1,
        )
        empty_role = ProjectRole.objects.create(
            project=project,
            name="Frontend",
            capacity=1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectRole.objects.create(
                project=project,
                name="Backend",
                capacity=2,
            )

        ProjectMember.objects.create(
            project=project,
            role=occupied_role,
            user=self.student_one,
        )

        # Занятую роль и используемое направление удалить нельзя.
        with self.assertRaises(RestrictedError), transaction.atomic():
            occupied_role.delete()
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.category.delete()

        # Незанятая роль и сам проект удаляются штатно.
        empty_role.delete()
        self.assertEqual(project.roles.count(), 1)
        project.delete()
        self.assertEqual(ProjectMember.objects.count(), 0)
        self.assertEqual(ProjectRole.objects.count(), 0)


class ProjectAdminTests(TestCase):
    def setUp(self):
        self.superuser = make_user("admin@example.com", superuser=True)
        self.student = make_user("member@example.com")
        self.client.force_login(self.superuser)
        self.category = Category.objects.create(name="Наука", slug="science")

    def test_all_project_models_registered_and_accessible_in_admin(self):
        project = Project.objects.create(
            author=self.superuser,
            category=self.category,
            title="Тестовый проект",
        )
        role = ProjectRole.objects.create(
            project=project,
            name="Backend",
            capacity=2,
        )
        member = ProjectMember.objects.create(
            project=project,
            role=role,
            user=self.student,
        )
        instances = {
            Category: self.category,
            Project: project,
            ProjectRole: role,
            ProjectMember: member,
        }
        for model, obj in instances.items():
            self.assertIn(model, admin.site._registry)
            meta = model._meta
            changelist = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
            add_url = reverse(f"admin:{meta.app_label}_{meta.model_name}_add")
            change_url = reverse(
                f"admin:{meta.app_label}_{meta.model_name}_change",
                args=[obj.pk],
            )
            self.assertEqual(self.client.get(changelist).status_code, 200)
            self.assertEqual(self.client.get(add_url).status_code, 200)
            self.assertEqual(self.client.get(change_url).status_code, 200)

    def test_admin_can_create_project_with_multiple_roles_and_member(self):
        response = self.client.post(
            reverse("admin:projects_project_add"),
            data={
                "author": str(self.superuser.pk),
                "category": str(self.category.pk),
                "title": "Исследование графовых нейросетей",
                "description": "Командный научный проект.",
                "status": Project.Status.OPEN,
                "roles-TOTAL_FORMS": "2",
                "roles-INITIAL_FORMS": "0",
                "roles-MIN_NUM_FORMS": "0",
                "roles-MAX_NUM_FORMS": "1000",
                "roles-0-name": "ML-инженер",
                "roles-0-description": "Обучение моделей",
                "roles-0-capacity": "2",
                "roles-0-is_open": "on",
                "roles-1-name": "Аналитик",
                "roles-1-description": "Подготовка датасета",
                "roles-1-capacity": "1",
                "roles-1-is_open": "on",
                "memberships-TOTAL_FORMS": "0",
                "memberships-INITIAL_FORMS": "0",
                "memberships-MIN_NUM_FORMS": "0",
                "memberships-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)

        project = Project.objects.get(title="Исследование графовых нейросетей")
        self.assertEqual(project.roles.count(), 2)
        ml_role = project.roles.get(name="ML-инженер")

        add_member = self.client.post(
            reverse("admin:projects_projectmember_add"),
            data={
                "project": str(project.pk),
                "role": str(ml_role.pk),
                "user": str(self.student.pk),
            },
        )
        self.assertEqual(add_member.status_code, 302)
        self.assertEqual(ml_role.occupied_places, 1)

        # Роль чужого проекта в админке возвращает ошибку формы, а не 500.
        other_project = Project.objects.create(
            author=self.superuser,
            category=self.category,
            title="Другой проект",
        )
        foreign_role = ProjectRole.objects.create(
            project=other_project,
            name="Дизайнер",
            capacity=1,
        )
        invalid_post = self.client.post(
            reverse("admin:projects_projectmember_add"),
            data={
                "project": str(project.pk),
                "role": str(foreign_role.pk),
                "user": str(self.superuser.pk),
            },
        )
        self.assertEqual(invalid_post.status_code, 200)
        self.assertEqual(ProjectMember.objects.count(), 1)
