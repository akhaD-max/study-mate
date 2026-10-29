from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from projects.selectors import get_project, list_roles
from projects.views import detail_context

from .forms import ApplicationForm
from .services import list_my_applications, submit_application


@login_required(login_url="accounts:login")
@require_POST
def submit(request, project_id):
    get_project(project_id)
    form = ApplicationForm(request.POST, roles=list_roles(project_id))
    if form.is_valid():
        try:
            submit_application(
                user=request.user, project_id=project_id,
                role_id=form.cleaned_data["projectRoleId"],
                comment=form.cleaned_data["comment"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Заявка успешно отправлена!")
            return redirect("applications:mine")
    return render(
        request, "projects/detail.html", detail_context(request.user, project_id, form),
    )


@login_required(login_url="accounts:login")
@require_GET
def mine(request):
    return render(
        request, "applications/my_applications.html",
        {"applications": list_my_applications(request.user)},
    )
