from django.http import Http404

from applications.storage import get_store


def list_projects():
    store = get_store()
    with store.lock:
        return [p for p in store.projects.values() if p.status == "open"]


def get_project(project_id):
    store = get_store()
    with store.lock:
        try:
            return store.projects[project_id]
        except KeyError:
            raise Http404("Проект не найден.") from None


def list_roles(project_id):
    store = get_store()
    with store.lock:
        return [r for r in store.roles.values() if r.project_id == project_id]
