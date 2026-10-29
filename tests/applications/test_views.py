from django.test import Client, override_settings
from django.urls import reverse

from applications.models import Application
from tests.applications import test_services


@override_settings(ROOT_URLCONF="applications.demo_urls")
class ApplicationViewTests(test_services.ApplicationServiceTests):
    def test_http_submission_csrf_privacy_and_stale_form(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        detail = reverse("projects:detail", args=[self.project.pk])
        submit = reverse("applications:submit", args=[self.project.pk])
        self.assertEqual(client.get(detail).status_code, 200)
        data = {"projectRoleId": str(self.role.pk), "comment": "Letter <script>"}
        self.assertEqual(client.post(submit, data).status_code, 403)
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        response = client.post(submit, data)
        self.assertRedirects(response, reverse("applications:mine"))
        self.assertContains(client.get(response.url), "Letter &lt;script&gt;")
        self.assertEqual(client.post(submit, data).status_code, 200)
        self.assertEqual(Application.objects.count(), 1)
        client.force_login(self.other)
        self.assertNotContains(client.get(response.url), "Letter")
        self.assertEqual(client.get(submit).status_code, 405)
        client.logout()
        self.assertEqual(client.get(detail).status_code, 302)

    def test_closed_role_preserves_comment(self):
        self.client.force_login(self.student)
        self.role.is_open = False
        self.role.save()
        response = self.client.post(
            reverse("applications:submit", args=[self.project.pk]),
            {"projectRoleId": str(self.role.pk), "comment": "Keep letter"},
        )
        self.assertContains(response, "Keep letter")
        self.assertFalse(Application.objects.exists())
