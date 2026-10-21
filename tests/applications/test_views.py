from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse


def detail_url():
    return reverse("projects:detail", args=[UUID(int=1)])


def submit_url():
    return reverse("applications:submit", args=[UUID(int=1)])


def csrf(browser):
    browser.get(detail_url())
    return browser.cookies["csrftoken"].value


def test_post_redirect_list_and_second_tab(store, browser):
    token = csrf(browser)
    browser.get(detail_url())  # A second tab opened before submission.
    data = {"projectRoleId": str(UUID(int=2)), "comment": "Моё письмо",
            "csrfmiddlewaretoken": token, "user_id": "victim", "project_id": "99"}
    response = browser.post(submit_url(), data)
    assert response.status_code == 302
    assert response.url == reverse("applications:mine")
    assert store.applications[0].student_id == "student-1"
    assert store.applications[0].project.id == UUID(int=1)
    assert "Моё письмо" in browser.get(response.url).content.decode()
    duplicate = browser.post(submit_url(), data)
    assert duplicate.status_code == 200
    assert "уже отправлена" in duplicate.content.decode()
    assert "Моё письмо" in duplicate.content.decode()
    assert len(store.applications) == 1
    browser.user = SimpleNamespace(pk="student-2", is_authenticated=True)
    assert "Моё письмо" not in browser.get(reverse("applications:mine")).content.decode()


@pytest.mark.parametrize("case", ["long", "missing_role", "closed_after_get", "full_after_get"])
def test_error_preserves_comment(store, browser, case):
    token = csrf(browser)
    role = store.roles[UUID(int=2)]
    if case == "closed_after_get":
        store.roles[role.id] = replace(role, is_open=False)
    elif case == "full_after_get":
        store.roles[role.id] = replace(role, filled_places=2)
    comment = "x" * 301 if case == "long" else "Не терять письмо <script>"
    response = browser.post(submit_url(), {
        "projectRoleId": "" if case == "missing_role" else str(role.id),
        "comment": comment, "csrfmiddlewaretoken": token,
    })
    assert response.status_code == 200
    assert ("x" * 301 if case == "long" else "Не терять письмо &lt;script&gt;") in response.content.decode()
    assert not store.applications


def test_no_csrf_no_auth_wrong_method_and_missing_project(store, browser):
    data = {"projectRoleId": str(UUID(int=2))}
    assert browser.post(submit_url(), data).status_code == 403
    token = csrf(browser)
    assert browser.get(submit_url()).status_code == 405
    assert browser.post(reverse("projects:catalog"), {"csrfmiddlewaretoken": token}).status_code == 405
    assert browser.post(reverse("applications:submit", args=[UUID(int=99)]), {
        **data, "csrfmiddlewaretoken": token,
    }).status_code == 404
    browser.user = AnonymousUser()
    assert browser.post(submit_url(), {**data, "csrfmiddlewaretoken": token}).status_code == 302
    assert browser.get(reverse("applications:mine")).status_code == 302
    assert not store.applications
