from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase

from applications.models import Application
from projects.management.commands.seed_demo import (
    DEMO_AUTHOR,
    DEMO_STUDENTS,
)
from projects.models import Category, Project, ProjectMember, ProjectRole

User = get_user_model()

DEMO_PASS = "demo-pass-123"


class SeedDemoCommandTests(TestCase):
    def test_requires_password_and_minimum_length(self):
        with (
            patch.dict("os.environ", {}, clear=False),
            self.assertRaises(CommandError),
        ):
            call_command("seed_demo")

        with self.assertRaises(CommandError):
            call_command("seed_demo", password="12345")

        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(Application.objects.count(), 0)

    def test_populates_users_projects_roles_memberships_and_statuses(self):
        out = StringIO()
        call_command("seed_demo", password=DEMO_PASS, stdout=out)

        self.assertIn("Демонстрационные данные готовы", out.getvalue())

        author = User.objects.get(email=DEMO_AUTHOR["email"])
        student_one = User.objects.get(email=DEMO_STUDENTS[0]["email"])
        student_two = User.objects.get(email=DEMO_STUDENTS[1]["email"])

        for account in (author, student_one, student_two):
            self.assertNotEqual(account.password, DEMO_PASS)
            self.assertTrue(account.password.startswith("pbkdf2_sha256$"))
            self.assertEqual(
                authenticate(username=account.email, password=DEMO_PASS),
                account,
            )

        self.assertGreaterEqual(Project.objects.count(), 3)

        main_project = Project.objects.get(title="Платформа учебных команд StudyMate")
        free_role = main_project.roles.get(name="Backend-разработчик")
        occupied_role = main_project.roles.get(name="Frontend-разработчик")
        closed_role = main_project.roles.get(name="UI/UX дизайнер")

        # 1) Свободная роль готова для успешной подачи заявки первым студентом.
        self.assertTrue(free_role.is_open)
        self.assertGreater(free_role.free_places, 0)
        self.assertTrue(free_role.is_available)
        self.assertFalse(
            Application.objects.filter(
                project=main_project,
                user=student_one,
            ).exists()
        )
        self.assertFalse(
            ProjectMember.objects.filter(
                project=main_project,
                user=student_one,
            ).exists()
        )

        # 2) Занятая роль заполнена участником через ProjectMember, свободных мест 0.
        self.assertTrue(occupied_role.is_open)
        self.assertEqual(occupied_role.occupied_places, occupied_role.capacity)
        self.assertEqual(occupied_role.free_places, 0)
        self.assertFalse(occupied_role.is_available)
        self.assertTrue(
            ProjectMember.objects.filter(
                project=main_project,
                role=occupied_role,
                user=student_two,
            ).exists()
        )

        # 3) Закрытая роль и закрытый по статусу проект недоступны для набора.
        self.assertFalse(closed_role.is_open)
        self.assertFalse(closed_role.is_available)
        closed_project = Project.objects.get(
            title="Аналитика вовлечённости онлайн-курсов"
        )
        self.assertNotEqual(closed_project.status, Project.Status.OPEN)
        self.assertFalse(closed_project.roles.first().is_available)

        # 4) Образцы всех трёх статусов присутствуют у первого студента,
        # а активный дубль на проекте с pending блокируется PostgreSQL.
        statuses = set(
            Application.objects.filter(user=student_one).values_list(
                "status", flat=True
            )
        )
        self.assertEqual(
            statuses,
            {
                Application.Status.PENDING,
                Application.Status.ACCEPTED,
                Application.Status.REJECTED,
            },
        )

        duplicate_project = Project.objects.get(
            title="Телеграм-бот расписания и дедлайнов"
        )
        qa_role = duplicate_project.roles.get(name="QA-инженер")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.create(
                user=student_one,
                project=duplicate_project,
                role=qa_role,
                comment="Повторная активная заявка",
            )

    def test_accepts_password_from_environment_variable(self):
        env_pass = "env-secret-789"
        with patch.dict(
            "os.environ",
            {"SEED_DEMO_PASSWORD": env_pass},
            clear=False,
        ):
            call_command("seed_demo", stdout=StringIO())

        student = User.objects.get(email=DEMO_STUDENTS[0]["email"])
        self.assertEqual(
            authenticate(username=student.email, password=env_pass),
            student,
        )

    def test_rerun_is_idempotent_and_preserves_manual_applications_and_real_users(
        self,
    ):
        real_user = User.objects.create_user(
            "real.student@university.edu",
            "my-personal-password-99",
        )
        original_real_hash = real_user.password

        call_command("seed_demo", password=DEMO_PASS, stdout=StringIO())

        counts_after_first = (
            User.objects.count(),
            Category.objects.count(),
            Project.objects.count(),
            ProjectRole.objects.count(),
            ProjectMember.objects.count(),
            Application.objects.count(),
        )

        student_one = User.objects.get(email=DEMO_STUDENTS[0]["email"])
        main_project = Project.objects.get(title="Платформа учебных команд StudyMate")
        free_role = main_project.roles.get(name="Backend-разработчик")

        # Студент вручную подаёт заявку в ходе проверки, а реальный студент — свою.
        manual_app = Application.objects.create(
            user=student_one,
            project=main_project,
            role=free_role,
            comment="Отклик, созданный вручную во время приёмки",
        )
        real_user_app = Application.objects.create(
            user=real_user,
            project=main_project,
            role=free_role,
            comment="Заявка реального пользователя",
        )

        # Меняем исходную демо-заявку, проверяя отсутствие сброса при повторе.
        duplicate_project = Project.objects.get(
            title="Телеграм-бот расписания и дедлайнов"
        )
        seeded_pending = Application.objects.get(
            user=student_one,
            project=duplicate_project,
        )
        seeded_pending.status = Application.Status.ACCEPTED
        seeded_pending.comment = "Обновлено при ручной проверке"
        seeded_pending.save()

        # Повторный запуск не должен плодить дубли или сбрасывать проверочные заявки.
        call_command("seed_demo", password=DEMO_PASS, stdout=StringIO())

        self.assertEqual(
            (
                User.objects.count(),
                Category.objects.count(),
                Project.objects.count(),
                ProjectRole.objects.count(),
                ProjectMember.objects.count(),
                Application.objects.count(),
            ),
            (
                counts_after_first[0],
                counts_after_first[1],
                counts_after_first[2],
                counts_after_first[3],
                counts_after_first[4],
                counts_after_first[5] + 2,
            ),
        )

        manual_app.refresh_from_db()
        real_user_app.refresh_from_db()
        seeded_pending.refresh_from_db()
        real_user.refresh_from_db()

        self.assertEqual(
            manual_app.comment,
            "Отклик, созданный вручную во время приёмки",
        )
        self.assertEqual(manual_app.status, Application.Status.PENDING)
        self.assertEqual(real_user_app.status, Application.Status.PENDING)
        self.assertEqual(seeded_pending.status, Application.Status.ACCEPTED)
        self.assertEqual(
            seeded_pending.comment,
            "Обновлено при ручной проверке",
        )
        self.assertEqual(real_user.password, original_real_hash)

    def test_no_data_migrations_exist_only_schema_migrations(self):
        root = Path(__file__).resolve().parents[2]
        migration_files = sorted(root.glob("*/migrations/0*.py"))
        self.assertEqual(
            [p.relative_to(root).as_posix() for p in migration_files],
            [
                "accounts/migrations/0001_initial.py",
                "applications/migrations/0001_initial.py",
                "projects/migrations/0001_initial.py",
            ],
        )
