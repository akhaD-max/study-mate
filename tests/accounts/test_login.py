from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "StudyMate-login-test-2026!"


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("student@example.com", PASSWORD)
        cls.inactive_user = User.objects.create_user(
            "inactive@example.com", PASSWORD, is_active=False
        )

    def setUp(self):
        self.url = reverse("accounts:login")
        self.home = reverse("main:home")

    def test_login_page_displays_form_and_registration_link(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, reverse("accounts:register"))

    def test_valid_email_ignores_case_and_session_survives_next_request(self):
        response = self.client.post(
            self.url, {"username": "STUDENT@EXAMPLE.COM", "password": PASSWORD}
        )

        self.assertRedirects(response, self.home, fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        home = self.client.get(self.home)
        self.assertEqual(home.wsgi_request.user.pk, self.user.pk)

    def test_wrong_password_and_unknown_email_have_same_error(self):
        messages = []
        for email in (self.user.email, "unknown@example.com"):
            with self.subTest(email=email):
                response = self.client.post(
                    self.url, {"username": email, "password": "wrong-password"}
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context["form"].non_field_errors().as_data()[0].code,
                    "invalid_login",
                )
                messages.append(str(response.context["form"].non_field_errors()))
                self.assertNotIn(SESSION_KEY, self.client.session)
                self.assertContains(response, email)
                self.assertNotContains(response, 'value="wrong-password"')
        self.assertEqual(messages[0], messages[1])

    def test_empty_fields_show_required_errors(self):
        response = self.client.post(self.url, {"username": "", "password": ""})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"username", "password"})
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_log_in(self):
        response = self.client.post(
            self.url, {"username": self.inactive_user.email, "password": PASSWORD}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_authenticated_user_is_redirected_to_home(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertRedirects(response, self.home, fetch_redirect_response=False)

    def test_internal_next_survives_form_submission(self):
        target = reverse("accounts:register")
        page = self.client.get(self.url, {"next": target})
        self.assertContains(page, f'<input type="hidden" name="next" value="{target}">')

        response = self.client.post(
            self.url,
            {"username": self.user.email, "password": PASSWORD, "next": target},
        )

        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_external_next_is_replaced_with_home(self):
        for target in ("https://example.org/", "//example.org/"):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(
                    self.url,
                    {"username": self.user.email, "password": PASSWORD, "next": target},
                )

                self.assertRedirects(response, self.home, fetch_redirect_response=False)

    def test_csrf_is_required_and_token_from_page_allows_login(self):
        client = Client(enforce_csrf_checks=True)
        credentials = {"username": self.user.email, "password": PASSWORD}

        rejected = client.post(self.url, credentials)
        self.assertEqual(rejected.status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

        client.get(self.url)
        response = client.post(
            self.url,
            {**credentials, "csrfmiddlewaretoken": client.cookies["csrftoken"].value},
        )
        self.assertRedirects(response, self.home, fetch_redirect_response=False)
        self.assertEqual(client.session[SESSION_KEY], str(self.user.pk))
