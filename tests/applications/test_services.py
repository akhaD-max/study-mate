from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from applications.models import Application
from applications.services import list_my_applications, submit_application
from projects.models import Category, Project, ProjectMember, ProjectRole


class ApplicationServiceTests(TransactionTestCase):
    def setUp(self):
        users = get_user_model().objects
        self.author = users.create_user(email="author@example.com", password="secret123")
        self.student = users.create_user(email="student@example.com", password="secret123")
        self.other = users.create_user(email="other@example.com", password="secret123")
        self.project = Project.objects.create(
            author=self.author, category=Category.objects.create(name="Development"),
            title="Test project",
        )
        self.role = ProjectRole.objects.create(project=self.project, name="Backend", capacity=1)

    def send(self, **kwargs):
        return submit_application(
            user=kwargs.pop("user", self.student), project_id=self.project.pk,
            role_id=kwargs.pop("role_id", self.role.pk), **kwargs,
        )

    def test_saved_pending_private_list_and_duplicate(self):
        saved = self.send(comment="Letter")
        saved.refresh_from_db()
        self.assertEqual(saved.user_id, self.student.pk)
        self.assertEqual(saved.status, Application.Status.PENDING)
        self.assertEqual(list(list_my_applications(self.student)), [saved])
        self.assertFalse(list_my_applications(self.other).exists())
        self.assertEqual(self.role.occupied_places, 0)
        with self.assertRaises(ValidationError):
            self.send()
        self.assertEqual(Application.objects.count(), 1)

    def test_rejected_allows_reapplication(self):
        saved = self.send()
        saved.status = Application.Status.REJECTED
        saved.save()
        self.assertNotEqual(self.send().pk, saved.pk)

    def test_author_member_closed_full_and_invalid_role(self):
        for arguments in ({"user": self.author}, {"comment": "x" * 301}, {"role_id": "invalid"}):
            with self.assertRaises(ValidationError):
                self.send(**arguments)
        self.role.is_open = False
        self.role.save()
        with self.assertRaises(ValidationError):
            self.send()
        self.role.is_open = True
        self.role.save()
        ProjectMember.objects.create(project=self.project, role=self.role, user=self.other)
        with self.assertRaises(ValidationError):
            self.send()
        with self.assertRaises(ValidationError):
            self.send(user=self.other)
        self.assertFalse(Application.objects.exists())

    def test_closed_project_and_foreign_role(self):
        foreign = Project.objects.create(
            author=self.author, category=self.project.category, title="Other project",
        )
        role = ProjectRole.objects.create(project=foreign, name="Design", capacity=1)
        with self.assertRaises(ValidationError):
            self.send(role_id=role.pk)
        self.project.status = Project.Status.COMPLETED
        self.project.save()
        with self.assertRaises(ValidationError):
            self.send()

    def test_concurrent_duplicate_uses_separate_connections(self):
        self.assertEqual(connection.vendor, "postgresql")
        barrier = Barrier(2)

        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                self.send()
                return "saved"
            except ValidationError:
                return "duplicate"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(results), ["duplicate", "saved"])
        self.assertEqual(Application.objects.count(), 1)

    def test_anonymous_cannot_submit(self):
        with self.assertRaises(PermissionDenied):
            self.send(user=AnonymousUser())
        self.assertFalse(Application.objects.exists())

    def test_pending_does_not_reserve_last_place_for_other_student(self):
        self.send(comment="x" * 300)
        self.send(user=self.other)
        self.assertEqual(Application.objects.count(), 2)
        self.role.refresh_from_db()
        self.assertEqual(self.role.free_places, 1)

    def test_concurrent_students_can_apply_for_same_last_place(self):
        barrier = Barrier(2)

        def attempt(user):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.send(user=user).pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            saved = list(pool.map(attempt, [self.student, self.other]))
        self.assertEqual(len(set(saved)), 2)
        self.assertEqual(Application.objects.filter(status=Application.Status.PENDING).count(), 2)
        self.role.refresh_from_db()
        self.assertEqual(self.role.free_places, 1)

    def test_pending_on_another_role_blocks_second_application(self):
        self.send()
        role = ProjectRole.objects.create(project=self.project, name="Design", capacity=1)
        with self.assertRaises(ValidationError):
            self.send(role_id=role.pk)
        self.assertEqual(Application.objects.count(), 1)

    def test_all_non_open_statuses_block_submission(self):
        for status in (Project.Status.IN_PROGRESS, Project.Status.COMPLETED,
                       Project.Status.CANCELLED):
            self.project.status = status
            self.project.save()
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.send()
        self.assertFalse(Application.objects.exists())
