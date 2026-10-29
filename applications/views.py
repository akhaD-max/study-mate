from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.vary import vary_on_headers

from accounts.decorators import session_required
from projects.selectors import get_project, list_roles
from projects.views import detail_context

from .forms import ApplicationForm
from .models import Application
from .services import (
    leave_project,
    list_my_applications,
    list_project_applications,
    review_application,
    submit_application,
    withdraw_application,
)


@session_required
@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request")
def submit(request, project_id):
    get_project(project_id)
    form = ApplicationForm(
        request.POST if request.method == "POST" else None, roles=list_roles(project_id),
    )
    htmx = request.headers.get("HX-Request") == "true"
    if request.method == "POST" and form.is_valid():
        try:
            application = submit_application(
                user=request.user, project_id=project_id,
                role_id=form.cleaned_data["projectRoleId"],
                comment=form.cleaned_data["comment"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            if htmx:
                response = render(request, "applications/partials/sent.html", {
                    "application": application,
                })
                response.headers["HX-Retarget"] = "#application-form"
                response.headers["HX-Reswap"] = "outerHTML"
                return response
            messages.success(request, "Заявка успешно отправлена!")
            return redirect("applications:mine")
    template = "applications/partials/form.html" if htmx else "applications/apply.html"
    response = render(request, template, detail_context(request.user, project_id, form))
    if htmx:
        response.headers["HX-Retarget"] = "#application-form"
        response.headers["HX-Reswap"] = "outerHTML"
    return response


@session_required
@require_GET
def mine(request):
    return render(request, "applications/my_applications.html", {
        "applications": list_my_applications(request.user),
    })


@session_required
@require_GET
def incoming(request, project_id):
    project, applications = list_project_applications(user=request.user, project_id=project_id)
    return render(request, "applications/incoming.html", {
        "project": project, "applications": applications,
    })


@session_required
@require_POST
def review(request, application_id, accept):
    try:
        application = review_application(
            user=request.user, application_id=application_id, accept=accept,
        )
    except ValidationError as error:
        candidate = get_object_or_404(Application, pk=application_id)
        project, applications = list_project_applications(
            user=request.user, project_id=candidate.project_id,
        )
        return render(request, "applications/incoming.html", {
            "project": project, "applications": applications, "errors": error.messages,
        })
    return redirect("applications:incoming", project_id=application.project_id)


@session_required
@require_POST
def withdraw(request, application_id):
    try:
        withdraw_application(user=request.user, application_id=application_id)
    except ValidationError as error:
        return render(request, "applications/my_applications.html", {
            "applications": list_my_applications(request.user), "errors": error.messages,
        })
    return redirect("applications:mine")


@session_required
@require_POST
def leave(request, project_id):
    try:
        leave_project(user=request.user, project_id=project_id)
    except ValidationError as error:
        context = detail_context(request.user, project_id)
        context["errors"] = error.messages
        return render(request, "projects/detail.html", context)
    return redirect("projects:detail", project_id=project_id)
