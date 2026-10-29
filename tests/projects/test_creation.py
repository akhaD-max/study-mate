from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from projects.forms import ProjectCreateForm, ProjectRoleFormSet
from projects.models import Category, Project, ProjectRole
from projects.services import create_project


class ProjectCreationTests(TransactionTestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(email="author@example.com")
        self.category = Category.objects.create(name="Разработка")

    def create(self, **overrides):
        data = {
            "author": self.author, "title": "Учебный проект", "description": "Описание",
            "category_id": self.category.pk,
            "roles": [{"name": "Backend", "capacity": 1}],
        }
        return create_project(**(data | overrides))

    def test_create_normalizes_text_and_saves_open_roles(self):
        project = self.create(title="  Учебный проект  ", roles=[
            {"name": " Backend ", "capacity": 1}, {"name": "Дизайнер", "capacity": 20},
        ])
        self.assertEqual(project.title, "Учебный проект")
        self.assertEqual(project.author, self.author)
        self.assertEqual(project.status, Project.Status.OPEN)
        self.assertEqual(list(project.roles.values_list("name", "capacity")), [
            ("Backend", 1), ("Дизайнер", 20),
        ])
        self.assertTrue(all(role.is_available for role in project.roles.all()))
        self.assertFalse(project.memberships.exists())

    def test_invalid_data_leaves_no_partial_rows(self):
        for data in (
            {"title": "ab"}, {"title": "x" * 101}, {"description": "  "},
            {"description": "x" * 5001}, {"category_id": uuid4()},
            {"category_id": "invalid"}, {"roles": []},
            {"roles": [{"name": " ", "capacity": 1}]},
            {"roles": [{"name": "x" * 101, "capacity": 1}]},
            *({"roles": [{"name": "Backend", "capacity": value}]}
              for value in (0, 21, "wrong", 1.5)),
            {"roles": [{"name": " Backend ", "capacity": 1},
                       {"name": "backend", "capacity": 2}]},
        ):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                self.create(**data)
            self.assertFalse(Project.objects.exists())
            self.assertFalse(ProjectRole.objects.exists())

    def test_anonymous_author(self):
        with self.assertRaises(PermissionDenied):
            self.create(author=AnonymousUser())
        self.assertFalse(Project.objects.exists())

    def test_duplicate_title_is_validation_error_and_other_author_allowed(self):
        self.create()
        with self.assertRaises(ValidationError) as caught:
            self.create()
        self.assertIn("title", caught.exception.message_dict)
        other = get_user_model().objects.create_user(email="other@example.com")
        self.create(author=other)
        self.assertEqual(Project.objects.count(), 2)
        self.assertEqual(ProjectRole.objects.count(), 2)

    def test_error_while_saving_second_role_rolls_back_project_and_first_role(self):
        original = ProjectRole.objects.create
        with patch("projects.services.ProjectRole.objects.create") as mocked:
            # Первый вызов действительно сохраняет роль перед ошибкой второго.
            def save_role(**kwargs):
                if mocked.call_count == 2:
                    raise RuntimeError("Ошибка записи")
                return original(**kwargs)
            mocked.side_effect = save_role
            with self.assertRaises(RuntimeError):
                self.create(roles=[{"name": "A", "capacity": 1},
                                   {"name": "B", "capacity": 2}])
        self.assertFalse(Project.objects.exists())
        self.assertFalse(ProjectRole.objects.exists())

    def test_form_fields_and_formset_management(self):
        form = ProjectCreateForm({"title": "Проект", "description": "Описание",
                                  "category_id": str(self.category.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["category_id"], self.category)
        for data in ({}, {"roles-TOTAL_FORMS": 0, "roles-INITIAL_FORMS": 0}):
            formset = ProjectRoleFormSet(data)
            self.assertEqual(formset.prefix, "roles")
            self.assertFalse(formset.is_valid())
        formset = ProjectRoleFormSet({
            "roles-TOTAL_FORMS": 2, "roles-INITIAL_FORMS": 0,
            "roles-0-name": " Backend ", "roles-0-capacity": 1,
            "roles-1-name": "backend", "roles-1-capacity": 2,
        })
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors())

    def test_concurrent_duplicate_title(self):
        self.assertEqual(connection.vendor, "postgresql")
        barrier = Barrier(2)

        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                self.create()
                return "created"
            except ValidationError:
                return "duplicate"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, range(2))), ["created", "duplicate"])
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(ProjectRole.objects.count(), 1)
