"""No DB or pytest-django required for the temporary storage contract."""

import os
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import django
import pytest
from django.conf import settings

if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
    root = Path(__file__).resolve().parents[1]
    settings.configure(
        SECRET_KEY="test-only-key", USE_TZ=True, ALLOWED_HOSTS=["testserver"],
        STATIC_URL="/static/",
        ROOT_URLCONF="applications.demo_urls",
        APPLICATIONS_USE_DEMO_STORAGE=True,
        INSTALLED_APPS=[
            "django.contrib.auth", "django.contrib.contenttypes",
            "django.contrib.sessions", "django.contrib.messages", "django.contrib.admin",
            "django.contrib.staticfiles", "main", "accounts",
        ],
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [root / "templates", root / "applications" / "demo_templates"],
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": [
                "django.contrib.messages.context_processors.messages",
            ]},
        }],
    )
django.setup()

@pytest.fixture
def store(monkeypatch):
    from applications import storage
    from applications.storage import MemoryStore, Project, Role

    value = MemoryStore()
    project = Project(UUID(int=1), "Демопроект", "Описание", "author")
    role = Role(UUID(int=2), project.id, "Backend", total_places=2)
    value.projects[project.id] = project
    value.roles[role.id] = role
    monkeypatch.setattr(storage, "_demo_store", value)
    monkeypatch.setattr(settings, "APPLICATIONS_USE_DEMO_STORAGE", True, raising=False)
    return value


@pytest.fixture
def student():
    return SimpleNamespace(pk="student-1", is_authenticated=True)


@pytest.fixture
def browser(student):
    from django.contrib.messages.storage.cookie import CookieStorage
    from django.test import Client

    class StudentClient(Client):
        def request(self, **request):
            def attach_identity(environ):
                environ.user = self.user
                environ._messages = CookieStorage(environ)

            # Attach identity before Django's handler dispatch, without fake auth in app.
            original = self.handler.get_response

            def respond(incoming):
                attach_identity(incoming)
                return original(incoming)

            self.handler.get_response = respond
            try:
                return super().request(**request)
            finally:
                self.handler.get_response = original

    client = StudentClient(enforce_csrf_checks=True)
    client.user = student
    return client
