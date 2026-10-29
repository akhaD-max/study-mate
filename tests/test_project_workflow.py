from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import resolve, reverse

from applications.models import Application
from applications.services import review_application, submit_application
from projects.models import Category, Project, ProjectMember, ProjectRole


class WorkflowHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user(email="owner@example.com")
        cls.student = users.create_user(email="student@example.com")
        cls.other = users.create_user(email="other@example.com")
        cls.category = Category.objects.create(name="Разработка")
        cls.project = Project.objects.create(
            author=cls.owner, category=cls.category, title="Командный проект",
        )
        cls.role = ProjectRole.objects.create(project=cls.project, name="Backend", capacity=1)

    def setUp(self):
        self.client.force_login(self.student)
        self.detail = reverse("projects:detail", args=[self.project.pk])
        self.apply = reverse("applications:submit", args=[self.project.pk])
        self.data = {"projectRoleId": str(self.role.pk), "comment": "Хочу в команду <script>"}

    def project_data(self, **overrides):
        return {
            "title": "Новый проект", "description": "Моя идея",
            "category_id": str(self.category.pk),
            "roles-TOTAL_FORMS": "2", "roles-INITIAL_FORMS": "0",
            "roles-0-name": "Дизайнер", "roles-0-capacity": "2",
            "roles-1-name": "Разработчик", "roles-1-capacity": "3",
        } | overrides

    def test_real_settings_and_catalog_aliases_use_one_handler(self):
        self.assertEqual(settings.SETTINGS_MODULE, "config.settings")
        self.assertEqual(settings.ROOT_URLCONF, "config.urls")
        self.assertIn("applications", settings.INSTALLED_APPS)
        self.assertEqual(reverse("main:catalog"), reverse("projects:catalog"))
        from projects.views import catalog

        self.assertIs(resolve("/projects/").func, catalog)
        self.assertEqual(self.client.post("/projects/").status_code, 405)
        self.assertRedirects(self.client.get("/"), "/projects/")

    def test_creation_context_and_plain_post_uses_session_author(self):
        url = reverse("projects:create")
        response = self.client.get(url)
        self.assertIn("form", response.context)
        self.assertIn("role_formset", response.context)
        response = self.client.post(url, self.project_data(author=str(self.owner.pk)))
        project = Project.objects.get(title="Новый проект")
        self.assertEqual(project.author, self.student)
        self.assertEqual(project.roles.count(), 2)
        self.assertRedirects(response, reverse("projects:detail", args=[project.pk]))

    def test_creation_errors_preserve_both_forms_and_duplicate_service_error(self):
        url = reverse("projects:create")
        data = self.project_data(title="A", **{"roles-1-capacity": "21"})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertTrue(response.context["role_formset"].errors[1])
        self.assertContains(response, "Моя идея")
        self.assertContains(response, "Дизайнер")
        self.assertEqual(Project.objects.count(), 1)
        self.client.post(url, self.project_data())
        response = self.client.post(url, self.project_data())
        self.assertIn("title", response.context["form"].errors)
        self.assertEqual(Project.objects.count(), 2)
        response = self.client.post(url, {"title": "Без ролей"})
        self.assertTrue(response.context["role_formset"].non_form_errors())

    def test_adding_role_without_js_preserves_input_without_publishing(self):
        response = self.client.post(
            reverse("projects:create"), self.project_data(action="add_role"),
        )
        self.assertContains(response, "Моя идея")
        self.assertEqual(response.context["role_formset"].total_form_count(), 3)
        self.assertEqual(Project.objects.count(), 1)

    def test_detail_and_apply_share_context_and_get_does_not_submit(self):
        for url in (self.detail, self.apply):
            response = self.client.get(url)
            for key in ("project", "roles", "form", "can_apply", "application_block_reason"):
                self.assertIn(key, response.context)
            self.assertContains(response, 'hx-target="#application-form"')
            self.assertContains(response, 'hx-swap="outerHTML"')
        self.assertFalse(Application.objects.exists())
        self.assertEqual(self.client.get(reverse("projects:detail", args=[uuid4()])).status_code, 404)

    def test_plain_submission_privacy_and_session_applicant(self):
        response = self.client.post(self.apply, self.data | {"user": str(self.owner.pk)})
        self.assertRedirects(response, reverse("applications:mine"))
        application = Application.objects.get()
        self.assertEqual(application.user, self.student)
        self.assertEqual(application.status, "pending")
        self.assertEqual(self.role.occupied_places, 0)
        page = self.client.get(response.url)
        self.assertContains(page, "Хочу в команду &lt;script&gt;")
        self.assertEqual(list(page.context["applications"]), [application])
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(response.url), "Хочу в команду")
        self.assertEqual(self.client.get("/applications/my/").status_code, 200)

    def test_htmx_success_and_errors_are_replaceable_fragments(self):
        response = self.client.post(self.apply, self.data | {"comment": "x" * 301},
                                    HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="application-form"')
        self.assertNotContains(response, "<!doctype html>")
        self.assertContains(response, "x" * 301)
        self.assertFalse(Application.objects.exists())
        response = self.client.post(self.apply, self.data, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Заявка отправлена")
        self.assertNotContains(response, "<!doctype html>")
        self.assertEqual(response.headers["HX-Retarget"], "#application-form")
        self.assertEqual(response.headers["HX-Reswap"], "outerHTML")
        response = self.client.post(self.apply, self.data, HTTP_HX_REQUEST="true")
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "Хочу в команду &lt;script&gt;")
        self.assertEqual(Application.objects.count(), 1)

    def test_service_error_is_displayed_and_closed_role_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.apply, self.data)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertContains(response, "собственный проект")
        self.client.force_login(self.student)
        self.role.is_open = False
        self.role.save()
        response = self.client.post(self.apply, self.data)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Application.objects.exists())

    def test_accept_reject_leave_and_reapply_plain_post(self):
        self.client.post(self.apply, self.data)
        application = Application.objects.get()
        review = reverse("applications:incoming", args=[self.project.pk])
        accept = reverse("applications:accept", args=[application.pk])
        self.assertEqual(self.client.get(review).status_code, 403)
        self.assertEqual(self.client.post(accept).status_code, 403)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(review), "Хочу в команду &lt;script&gt;")
        self.assertRedirects(self.client.post(accept), review)
        self.assertRedirects(self.client.post(accept), review)
        self.assertEqual(ProjectMember.objects.count(), 1)
        application.refresh_from_db()
        self.assertEqual(application.status, "accepted")
        self.client.force_login(self.student)
        self.assertContains(self.client.get(self.detail), "Покинуть проект")
        self.assertContains(self.client.get(reverse("projects:mine")), self.project.title)
        leave = reverse("applications:leave", args=[self.project.pk])
        self.assertRedirects(self.client.post(leave), self.detail)
        self.assertRedirects(self.client.post(leave), self.detail)
        self.assertFalse(ProjectMember.objects.exists())
        self.assertEqual(self.role.free_places, 1)
        self.client.post(self.apply, self.data)
        pending = Application.objects.get(status="pending")
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(reverse("applications:reject", args=[pending.pk])), review)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "rejected")
        self.assertFalse(ProjectMember.objects.exists())

    def test_withdraw_only_own_pending_and_mutations_require_post(self):
        self.client.post(self.apply, self.data)
        application = Application.objects.get()
        withdraw = reverse("applications:withdraw", args=[application.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(withdraw).status_code, 403)
        self.client.force_login(self.student)
        for url in (withdraw, reverse("applications:accept", args=[application.pk]),
                    reverse("applications:reject", args=[application.pk]),
                    reverse("applications:leave", args=[self.project.pk])):
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(withdraw), reverse("applications:mine"))
        self.assertFalse(Application.objects.exists())

    def test_login_and_csrf_protect_all_mutating_operations(self):
        self.client.post(self.apply, self.data)
        application = Application.objects.get()
        routes = [
            reverse("projects:create"), self.apply,
            reverse("applications:accept", args=[application.pk]),
            reverse("applications:reject", args=[application.pk]),
            reverse("applications:withdraw", args=[application.pk]),
            reverse("applications:leave", args=[self.project.pk]),
        ]
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in routes:
            self.assertEqual(client.post(url, {}).status_code, 403)
        client.get(reverse("projects:create"))
        data = self.project_data(csrfmiddlewaretoken=client.cookies["csrftoken"].value)
        self.assertEqual(client.post(reverse("projects:create"), data).status_code, 302)
        self.client.logout()
        for url in [*routes, self.detail, reverse("applications:mine"), reverse("projects:mine")]:
            self.assertEqual(self.client.post(url).status_code, 302)
        expired = self.client.post(self.apply, self.data, HTTP_HX_REQUEST="true")
        self.assertEqual(expired.status_code, 200)
        self.assertIn("/accounts/login/?next=", expired.headers["HX-Redirect"])


class ReviewConcurrencyTests(TransactionTestCase):
    def test_two_candidates_for_last_place_are_serialized(self):
        self.assertEqual(connection.vendor, "postgresql")
        users = get_user_model().objects
        owner = users.create_user(email="owner@example.com")
        project = Project.objects.create(
            author=owner, category=Category.objects.create(name="Разработка"), title="Проект",
        )
        role = ProjectRole.objects.create(project=project, name="Backend", capacity=1)
        applications = [submit_application(
            user=users.create_user(email=f"student{index}@example.com"),
            project_id=project.pk, role_id=role.pk,
        ) for index in range(2)]
        barrier = Barrier(2)

        def accept(application):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                review_application(user=owner, application_id=application.pk, accept=True)
                return "accepted"
            except ValidationError:
                return "full"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(accept, applications)), ["accepted", "full"])
        self.assertEqual(ProjectMember.objects.count(), 1)
        self.assertEqual(Application.objects.filter(status="accepted").count(), 1)
        self.assertEqual(Application.objects.filter(status="pending").count(), 1)
