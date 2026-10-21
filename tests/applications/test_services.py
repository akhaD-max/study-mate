from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.core.exceptions import ValidationError

from applications.services import list_my_applications, submit_application
from applications.storage import Application, Project, Role


def send(student, **kwargs):
    return submit_application(
        user=student, project_id=UUID(int=1), role_id=UUID(int=2), **kwargs,
    )


def test_saved_pending_and_isolated_sorted_list(store, student):
    first = send(student, comment="Первое письмо")
    project = Project(UUID(int=3), "Другой", "", "author")
    role = Role(UUID(int=4), project.id, "Design")
    store.projects[project.id] = project
    store.roles[role.id] = role
    second = submit_application(user=student, project_id=project.id, role_id=role.id)
    assert first.status == "pending"
    assert store.roles[UUID(int=2)].filled_places == 0
    assert list_my_applications(student) == [second, first]
    assert list_my_applications(SimpleNamespace(pk="other")) == []


@pytest.mark.parametrize("case", ["author", "member", "closed", "role_closed", "full", "foreign", "missing", "pending", "accepted", "long"])
def test_rejected_submission_leaves_storage_unchanged(store, student, case):
    project = store.projects[UUID(int=1)]
    role = store.roles[UUID(int=2)]
    if case == "author":
        student.pk = "author"
    elif case == "member":
        store.memberships.add((project.id, student.pk))
    elif case == "closed":
        store.projects[project.id] = replace(project, status="completed")
    elif case == "role_closed":
        store.roles[role.id] = replace(role, is_open=False)
    elif case == "full":
        store.roles[role.id] = replace(role, filled_places=role.total_places)
    elif case == "foreign":
        store.roles[role.id] = replace(role, project_id=UUID(int=99))
    elif case == "missing":
        del store.roles[role.id]
    elif case in {"pending", "accepted"}:
        store.applications.append(Application(student.pk, project, role, "", status=case))
    before = len(store.applications)
    with pytest.raises(ValidationError):
        send(student, comment="x" * 301 if case == "long" else "")
    assert len(store.applications) == before


def test_concurrent_duplicate_creates_one_application(store, student):
    def attempt(_):
        try:
            send(student)
            return "saved"
        except ValidationError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == ["duplicate", "saved"]
    assert len(store.applications) == 1
