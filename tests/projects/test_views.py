from django.test import override_settings
from django.urls import reverse

from tests.applications import test_services


@override_settings(ROOT_URLCONF="applications.demo_urls")
class ProjectViewTests(test_services.ApplicationServiceTests):
    def test_detail_uses_model_role_fields(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.assertContains(response, self.role.name)
        self.assertContains(response, "0/1")
