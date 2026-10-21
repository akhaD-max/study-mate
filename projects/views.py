from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from applications.forms import ApplicationForm
from applications.services import application_block_reason
from applications.storage import get_store

from .selectors import get_project, list_projects, list_roles


def detail_context(user, project_id, form=None):
    store = get_store()
    with store.lock:
        project = get_project(project_id)
        roles = list_roles(project_id)
        reason = application_block_reason(store, project, str(user.pk))
        if not reason and not any(r.is_available for r in roles):
            reason = "Нет доступных ролей."
        return {
            "project": project, "roles": roles,
            "form": form if form is not None else ApplicationForm(roles=roles),
            "can_apply": not reason, "application_block_reason": reason,
        }


@login_required(login_url="accounts:login")
@require_GET
def catalog(request):
    return render(request, "projects/catalog.html", {"projects": list_projects()})


@login_required(login_url="accounts:login")
@require_GET
def detail(request, project_id):
    return render(request, "projects/detail.html", detail_context(request.user, project_id))
