import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from applications.models import Application
from projects.models import Category, Project, ProjectRole

User = get_user_model()

PASSWORD = "test-pass-12345"


def make_user(email: str, password: str = PASSWORD, *, superuser: bool = False):
    kwargs = {"email": email, "password": password}
    if User.USERNAME_FIELD != "email":
        kwargs[User.USERNAME_FIELD] = email
    if superuser:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class ApplicationModelTests(TestCase):
    def setUp(self):
        self.author = make_user("author@example.com")
        self.student = make_user("student@example.com")
        self.second_student = make_user("student2@example.com")
        self.category = Category.objects.create(
            name="Разработка",
            slug="development",
        )
        self.project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Сервис расписания",
            description="Учебный проект команды.",
        )
        self.backend_role = ProjectRole.objects.create(
            project=self.project,
            name="Backend-разработчик",
            capacity=2,
        )
        self.frontend_role = ProjectRole.objects.create(
            project=self.project,
            name="Frontend-разработчик",
            capacity=1,
        )

    def test_create_application_saves_selected_role_and_defaults(self):
        application = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.backend_role,
            comment="Опыт с Django и PostgreSQL.",
        )

        self.assertIsInstance(application.pk, uuid.UUID)
        self.assertEqual(application.user, self.student)
        self.assertEqual(application.project, self.project)
        self.assertEqual(application.role, self.backend_role)
        self.assertEqual(application.comment, "Опыт с Django и PostgreSQL.")
        self.assertEqual(application.status, Application.Status.PENDING)
        self.assertEqual(application.get_status_display(), "На рассмотрении")
        self.assertIsNotNone(application.created_at)
        self.assertIsNotNone(application.updated_at)

    def test_status_choices_and_russian_labels(self):
        self.assertEqual(
            Application.Status.choices,
            [
                ("pending", "На рассмотрении"),
                ("accepted", "Принята"),
                ("rejected", "Отклонена"),
            ],
        )

        application = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.backend_role,
        )
        self.assertEqual(application.comment, "")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.filter(pk=application.pk).update(status="withdrawn")

    def test_comment_max_length_300_in_clean_and_postgresql(self):
        exact = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.backend_role,
            comment="а" * 300,
        )
        self.assertEqual(len(exact.comment), 300)

        too_long = Application(
            user=self.second_student,
            project=self.project,
            role=self.backend_role,
            comment="б" * 301,
        )
        with self.assertRaises(ValidationError):
            too_long.full_clean()

        with self.assertRaises(DataError), transaction.atomic():
            Application.objects.create(
                user=self.second_student,
                project=self.project,
                role=self.backend_role,
                comment="б" * 301,
            )

    def test_unique_pending_application_per_project_and_user_in_postgresql(self):
        first = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.backend_role,
            comment="Первый отклик",
        )

        # Повторный активный отклик на ту же роль блокируется БД.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.create(
                user=self.student,
                project=self.project,
                role=self.backend_role,
                comment="Дубль на ту же роль",
            )

        # Активный отклик на другую роль того же проекта тоже блокируется БД.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.create(
                user=self.student,
                project=self.project,
                role=self.frontend_role,
                comment="Дубль на другую роль",
            )

        # Другой студент и другой проект откликаются свободно.
        other_user_app = Application.objects.create(
            user=self.second_student,
            project=self.project,
            role=self.backend_role,
        )
        other_project = Project.objects.create(
            author=self.author,
            category=self.category,
            title="Второй проект",
        )
        other_role = ProjectRole.objects.create(
            project=other_project,
            name="ML-инженер",
            capacity=1,
        )
        other_project_app = Application.objects.create(
            user=self.student,
            project=other_project,
            role=other_role,
        )
        self.assertEqual(other_user_app.status, Application.Status.PENDING)
        self.assertEqual(other_project_app.status, Application.Status.PENDING)

        # После отклонения прежней заявки частичный индекс не мешает новой подаче.
        first.status = Application.Status.REJECTED
        first.save()
        resubmitted = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.frontend_role,
            comment="Повторный отклик",
        )
        self.assertEqual(resubmitted.status, Application.Status.PENDING)

    def test_pending_application_does_not_occupy_role_place(self):
        Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.frontend_role,
        )
        self.assertEqual(self.frontend_role.occupied_places, 0)
        self.assertEqual(self.frontend_role.free_places, 1)
        self.assertTrue(self.frontend_role.is_available)


class ApplicationConcurrencyTests(TransactionTestCase):
    def test_concurrent_submissions_create_only_one_pending_application(self):
        author = make_user("lead@example.com")
        student = make_user("applicant@example.com")
        category = Category.objects.create(name="Аналитика", slug="analytics")
        project = Project.objects.create(
            author=author,
            category=category,
            title="Конкурентный отклик",
        )
        role_one = ProjectRole.objects.create(
            project=project,
            name="Backend",
            capacity=2,
        )
        role_two = ProjectRole.objects.create(
            project=project,
            name="Frontend",
            capacity=2,
        )
        barrier = Barrier(2)

        def submit_in_separate_connection(role):
            try:
                barrier.wait(timeout=5)
                with transaction.atomic():
                    Application.objects.create(
                        user_id=student.pk,
                        project_id=project.pk,
                        role_id=role.pk,
                        comment=f"Отклик на {role.name}",
                    )
                return "created"
            except IntegrityError:
                return "duplicate"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(submit_in_separate_connection, role_one),
                executor.submit(submit_in_separate_connection, role_two),
            ]
            outcomes = sorted(f.result() for f in futures)

        self.assertEqual(outcomes, ["created", "duplicate"])
        self.assertEqual(
            Application.objects.filter(
                project=project,
                user=student,
                status=Application.Status.PENDING,
            ).count(),
            1,
        )


class ApplicationAdminTests(TestCase):
    def setUp(self):
        self.superuser = make_user("admin@example.com", superuser=True)
        self.student = make_user("candidate@example.com")
        self.client.force_login(self.superuser)
        self.category = Category.objects.create(name="Дизайн", slug="design")
        self.project = Project.objects.create(
            author=self.superuser,
            category=self.category,
            title="Дизайн-система",
        )
        self.role = ProjectRole.objects.create(
            project=self.project,
            name="UI/UX дизайнер",
            capacity=2,
        )

    def test_application_registered_in_admin_without_decision_workflow_actions(self):
        self.assertIn(Application, admin.site._registry)
        model_admin = admin.site._registry[Application]
        self.assertEqual(model_admin.actions, ())

        application = Application.objects.create(
            user=self.student,
            project=self.project,
            role=self.role,
            comment="Портфолио в Figma",
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:applications_application_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin:applications_application_add")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:applications_application_change", args=[application.pk])
            ).status_code,
            200,
        )
