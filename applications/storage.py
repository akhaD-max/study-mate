"""Temporary, single-process storage. No ORM models or migrations."""

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


@dataclass(frozen=True)
class Project:
    id: UUID
    title: str
    description: str
    author_id: str
    status: str = "open"


@dataclass(frozen=True)
class Role:
    id: UUID
    project_id: UUID
    title: str
    total_places: int = 1
    filled_places: int = 0
    is_open: bool = True

    @property
    def is_available(self):
        return self.is_open and self.filled_places < self.total_places


@dataclass(frozen=True)
class Application:
    student_id: str
    project: Project
    role: Role
    comment: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=timezone.now)
    status: str = "pending"

    def get_status_display(self):
        return {
            "pending": "На рассмотрении",
            "accepted": "Принята",
            "rejected": "Отклонена",
        }.get(self.status, self.status)


class MemoryStore:
    def __init__(self):
        self.lock = RLock()
        self.projects = {}
        self.roles = {}
        self.applications = []
        self.memberships = set()  # (project UUID, str(student.pk))


_demo_store = MemoryStore()
_project_id = UUID(int=1)
_role_id = UUID(int=2)
_demo_store.projects[_project_id] = Project(
    _project_id, "StudyMate: демопроект", "Учебный проект для проверки отклика.",
    "demo-author",
)
_demo_store.roles[_role_id] = Role(_role_id, _project_id, "Backend-разработчик")


def get_store():
    if not getattr(settings, "APPLICATIONS_USE_DEMO_STORAGE", False):
        raise ImproperlyConfigured(
            "Модели ещё не подключены. Для демо используйте applications.demo_settings."
        )
    return _demo_store
