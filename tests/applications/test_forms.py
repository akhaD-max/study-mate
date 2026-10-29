from django.contrib.auth import get_user_model
from django.test import TestCase

from applications.forms import ApplicationForm
from projects.models import Category, Project, ProjectRole


class ApplicationFormTests(TestCase):
    def test_contract_fields_and_only_available_roles(self):
        author = get_user_model().objects.create_user(email="author@example.com")
        project = Project.objects.create(
            author=author, title="Проект", category=Category.objects.create(name="Учёба"),
        )
        opened = ProjectRole.objects.create(project=project, name="Backend", capacity=1)
        closed = ProjectRole.objects.create(
            project=project, name="Design", capacity=1, is_open=False,
        )
        roles = [opened, closed]
        for comment in ("", "x" * 300):
            form = ApplicationForm(
                {"projectRoleId": str(opened.pk), "comment": comment}, roles=roles,
            )
            self.assertTrue(form.is_valid(), form.errors)
        for data in (
            {"projectRoleId": str(closed.pk)}, {"projectRoleId": "invalid"}, {},
            {"projectRoleId": str(opened.pk), "comment": "x" * 301},
        ):
            self.assertFalse(ApplicationForm(data, roles=roles).is_valid())
