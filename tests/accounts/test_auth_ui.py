from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class AuthPageTests(SimpleTestCase):
    def test_pages_use_local_assets_and_only_two_fields(self):
        for name, email_name in (("login", "username"), ("register", "email")):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"accounts:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context["form"].fields), [email_name, "password"]
                )
                self.assertContains(response, 'type="email"')
                self.assertContains(response, 'type="password"')
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, 'id="auth-form"')
                self.assertContains(response, 'hx-target="#auth-form"')
                self.assertContains(response, "css/auth.css")
                self.assertContains(response, "js/auth.js")
                self.assertNotContains(response, "VK ID")
                self.assertNotContains(response, "Яндекс ID")
                self.assertNotContains(response, "cdn.tailwindcss.com")

    def test_invalid_htmx_forms_return_fragment_with_errors(self):
        for name in ("login", "register"):
            with self.subTest(page=name):
                response = self.client.post(
                    reverse(f"accounts:{name}"), {}, HTTP_HX_REQUEST="true"
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f"accounts/partials/{name}_form.html")
                self.assertContains(response, 'role="alert"')
                self.assertContains(response, 'aria-invalid="true"')
                self.assertNotContains(response, "<!doctype html>")

    def test_invalid_regular_forms_return_complete_pages(self):
        for name in ("login", "register"):
            response = self.client.post(reverse(f"accounts:{name}"), {})
            self.assertContains(response, "<!doctype html>")
            self.assertTrue(response.context["form"].errors)


class AuthSubmissionTests(TestCase):
    def test_htmx_login_redirect_and_session(self):
        user = get_user_model().objects.create_user(
            email="student@example.com", password="StudyMate-safe-password!"
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": "StudyMate-safe-password!"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], reverse("main:home"))
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))

    def test_registration_creates_user_and_logs_in_with_and_without_htmx(self):
        for htmx in (False, True):
            with self.subTest(htmx=htmx):
                self.client.logout()
                response = self.client.post(
                    reverse("accounts:register"),
                    {
                        "email": f"student{htmx}@example.com",
                        "password": "StudyMate-safe-password!",
                    },
                    **({"HTTP_HX_REQUEST": "true"} if htmx else {}),
                )
                user = get_user_model().objects.get(email=f"student{htmx}@example.com".lower())
                self.assertTrue(user.check_password("StudyMate-safe-password!"))
                self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
                if htmx:
                    self.assertEqual(
                        response.headers["HX-Redirect"], reverse("main:home")
                    )
                else:
                    self.assertRedirects(
                        response, reverse("main:home"), fetch_redirect_response=False,
                    )
