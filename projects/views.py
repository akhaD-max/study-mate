from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from applications.forms import ApplicationForm
from applications.services import application_block_reason

from .forms import ProjectCreateForm, ProjectRoleFormSet
from .models import Category, Project, ProjectRole
from .selectors import get_project, list_roles
from .services import create_project


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
        "members": project.memberships.select_related("user", "role"),
        "is_owner": project.author_id == user.pk,
        "is_member": project.memberships.filter(user=user).exists(),
    }


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def catalog(request):
    """Каталог открытых проектов с серверной фильтрацией и HTMX."""
    selected_direction = request.GET.get("direction", "").strip()
    search_query = request.GET.get("q", "").strip()[:200]
    sort = request.GET.get("sort", "newest")
    ordering = {
        "newest": ("-created_at", "pk"),
        "oldest": ("created_at", "pk"),
        "members": ("-member_count", "-created_at", "pk"),
        "fewer_members": ("member_count", "-created_at", "pk"),
    }
    if sort not in ordering:
        sort = "newest"

    projects = (
        Project.objects.filter(status=Project.Status.OPEN)
        .select_related("category", "author")
        .annotate(member_count=Count("memberships", distinct=True))
        .prefetch_related(
            Prefetch(
                "roles",
                queryset=ProjectRole.objects.filter(is_open=True).with_occupancy(),
                to_attr="catalog_roles",
            )
        )
    )
    if selected_direction:
        projects = projects.filter(category__slug=selected_direction)
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    page = Paginator(projects.order_by(*ordering[sort]), 12).get_page(
        request.GET.get("page")
    )
    context = {
        "projects": page,
        "page_obj": page,
        "project_count": page.paginator.count,
        "categories": Category.objects.all(),
        "selected_direction": selected_direction,
        "search_query": search_query,
        "sort": sort,
    }
    template = "projects/catalog.html"
    if (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    ):
        template = "projects/partials/catalog_content.html"
    return render(request, template, context)



@login_required
@require_http_methods(["GET", "POST"])
def create(request):
    data = request.POST if request.method == "POST" else None
    adding_role = data is not None and request.POST.get("action") == "add_role"
    if adding_role:
        data = data.copy()
        try:
            total = int(data.get("roles-TOTAL_FORMS", 0))
        except (TypeError, ValueError):
            total = 0
        data["roles-TOTAL_FORMS"] = str(min(max(total, 0) + 1, 1000))
    form = ProjectCreateForm(data)
    role_formset = ProjectRoleFormSet(data)
    if request.method == "POST" and not adding_role:
        valid_form = form.is_valid()
        valid_roles = role_formset.is_valid()
        if valid_form and valid_roles:
            try:
                project = create_project(
                    author=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category_id=form.cleaned_data["category_id"].pk,
                    roles=[role.cleaned_data for role in role_formset if role.cleaned_data],
                )
            except ValidationError as error:
                if hasattr(error, "error_dict"):
                    for field, errors in error.error_dict.items():
                        form.add_error(field if field in form.fields else None, errors)
                else:
                    form.add_error(None, error)
            else:
                return redirect("projects:detail", project_id=project.pk)
    return render(request, "projects/create.html", {"form": form, "role_formset": role_formset})


@login_required
@require_GET
def mine(request):
    projects = Project.objects.filter(
        Q(author=request.user) | Q(memberships__user=request.user)
    ).select_related("author", "category").distinct().order_by("-created_at", "pk")
    return render(request, "projects/mine.html", {"projects": projects})


@login_required
@require_GET
def detail(request, project_id):
    return render(request, "projects/detail.html", detail_context(request.user, project_id))
