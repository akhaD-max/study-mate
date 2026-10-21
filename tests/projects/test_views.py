from uuid import UUID

from django.urls import reverse


def test_catalog_detail_and_missing_project(store, browser):
    assert "Демопроект" in browser.get(reverse("projects:catalog")).content.decode()
    response = browser.get(reverse("projects:detail", args=[UUID(int=1)]))
    assert response.status_code == 200
    assert "Backend" in response.content.decode()
    assert "csrftoken" in response.cookies
    assert browser.get(reverse("projects:detail", args=[UUID(int=99)])).status_code == 404


def test_catalog_requires_login(store, browser):
    from django.contrib.auth.models import AnonymousUser

    browser.user = AnonymousUser()
    response = browser.get(reverse("projects:catalog"))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/?next=")
