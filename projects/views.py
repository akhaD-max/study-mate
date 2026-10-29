from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from applications.forms import ApplicationForm
from applications.services import application_block_reason

from .selectors import get_project, list_roles


def detail_context(user, project_id, form=None):
    project = get_project(project_id)
    roles = list(list_roles(project_id))
    reason = application_block_reason(project, user.pk)
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
    from main.views import catalog as catalog_view

    return catalog_view(request)


@login_required(login_url="accounts:login")
@require_GET
def detail(request, project_id):
    return render(request, "projects/detail.html", detail_context(request.user, project_id))
