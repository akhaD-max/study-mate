from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from applications.forms import ApplicationForm
from applications.models import Application
from applications.services import application_block_reason

from .forms import CatalogFilterForm, ProjectCreateForm, ProjectRoleFormSet
from .models import Category, Project, ProjectMember
from .selectors import (
    catalog_projects,
    get_project,
    list_catalog_role_names,
    list_roles,
)
from .services import create_project


def plural_ru(number, one, few, many):
    """Русское плюральное окончание для целых чисел."""
    mod10 = number % 10
    mod100 = number % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return few
    return many


def detail_context(user, project_id, form=None):
    project = get_project(project_id)
    roles = list(list_roles(project_id))
    reason = application_block_reason(project, user.pk)
    if not reason and not any(r.is_available for r in roles):
        reason = "Нет доступных ролей."
    members = list(project.memberships.select_related("user", "role"))
    team_count = len(members) + 1
    available_roles = [role for role in roles if role.is_available]
    for role in roles:
        role.free_places_label = (
            f"{role.free_places} "
            + plural_ru(role.free_places, "свободное место", "свободных места", "свободных мест")
        )
    default_form = None
    if form is None:
        # Первая доступная роль предвыбрана, как в макете отклика.
        default_form = ApplicationForm(
            roles=roles,
            initial={"projectRoleId": str(available_roles[0].id)} if available_roles else {},
        )
    return {
        "project": project, "roles": roles,
        "form": form if form is not None else default_form,
        "can_apply": not reason, "application_block_reason": reason,
        "members": members,
        "team_count": team_count,
        "team_label": f"Команда · {team_count} "
        + plural_ru(team_count, "участник", "участника", "участников"),
        "free_places_total": sum(role.free_places for role in roles),
        "open_roles_count": len(available_roles),
        "recruitment_open": project.status == Project.Status.OPEN and bool(available_roles),
        "looking_for": ", ".join(role.name for role in available_roles),
        "is_owner": project.author_id == user.pk,
        "is_member": any(member.user_id == user.pk for member in members),
    }


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def catalog(request):
    """HTTP-запрос → валидация → выборка БД → страница или HTMX-фрагмент."""
    form = CatalogFilterForm(request.GET)
    valid = form.is_valid()
    values = form.cleaned_data
    # На ошибочном запросе не выдаём список как будто поиск завершился успешно.
    projects = catalog_projects(
        q=values["q"], direction=values["direction"], role=values["role"],
        open_only=values["open_only"], sort=values["sort"],
    ) if valid else []
    page = Paginator(projects, 12).get_page(request.GET.get("page"))
    # Роли уже загружены через Prefetch: бейдж не создаёт запрос на карточку.
    for project in page:
        project.recruitment_open = project.status == Project.Status.OPEN and any(
            role.free_places > 0 for role in project.catalog_roles
        )
    categories = list(Category.objects.all())
    role_names = list(list_catalog_role_names())
    # Успешные поля показываем нормализованными; ошибочный ввод сохраняем,
    # чтобы пользователь мог исправить его, а не набирать условия заново.
    selected_direction = values.get("direction", form["direction"].value()) or ""
    selected_role = values.get("role", form["role"].value()) or ""
    search_query = values.get("q", form["q"].value()) or ""
    # Радиокнопки не умеют показывать невалидный ввод, поэтому при ошибке
    # сохраняем выбор по сырому значению: повтор open_only=false не должен
    # молча переключать интерфейс на «Только с открытым набором».
    raw_open_only = request.GET.get("open_only")
    selected_open_only = values.get(
        "open_only", raw_open_only != "false" if raw_open_only is not None else True
    )
    # «Нет данных» и «нет совпадений» различаются только смысловыми условиями:
    # page, sort и неизвестные параметры не превращают пустую базу в пустую выдачу.
    has_filters = bool(search_query or selected_direction or selected_role) or (
        raw_open_only == "false"
    )
    context = {
        "filter_form": form,
        "filter_errors": form.errors,
        "projects": page,
        "page_obj": page,
        "project_count": page.paginator.count,
        "categories": categories,
        "role_names": role_names,
        "selected_direction": selected_direction,
        "selected_direction_name": next(
            (category.name for category in categories if category.slug == selected_direction),
            selected_direction,
        ),
        "selected_role": selected_role,
        "unknown_direction": selected_direction and not any(
            category.slug == selected_direction for category in categories
        ),
        "unknown_role": selected_role and not any(
            name.lower() == selected_role.lower() for name in role_names
        ),
        "search_query": search_query,
        "sort": values.get("sort", "newest"),
        "open_only": selected_open_only,
        "has_filters": has_filters,
    }
    template = "projects/catalog.html"
    if (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    ):
        template = "projects/partials/catalog_content.html"
    return render(request, template, context, status=200 if valid else 400)



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
    context = {"form": form, "role_formset": role_formset}
    template = "projects/create.html"
    if adding_role and request.headers.get("HX-Request") == "true":
        # HTMX заменяет только набор ролей, не перерисовывая страницу целиком.
        template = "projects/partials/role_formset.html"
    return render(request, template, context)


@login_required
@require_GET
def mine(request):
    base = (
        Project.objects.filter(
            Q(author=request.user) | Q(memberships__user=request.user),
        )
        .select_related("author", "category")
        .distinct()
        .order_by("-created_at", "pk")
        .prefetch_related(Prefetch(
            "memberships",
            queryset=ProjectMember.objects.filter(user=request.user).select_related("role"),
            to_attr="my_membership",
        ))
    )
    # «Мои» небольшая выборка: счётчики считаем простыми запросами к одной и той же базе.
    raw_status = request.GET.get("status", "all")
    valid_statuses = {"all", *(value for value, _label in Project.Status.choices)}
    status = raw_status if raw_status in valid_statuses else "all"
    counts = {"all": base.count()}
    for value, _label in Project.Status.choices:
        counts[value] = base.filter(status=value).count()
    source = base if status == "all" else base.filter(status=status)
    projects = list(source)
    pending_map = dict(
        Application.objects.filter(
            project__in=projects, status=Application.Status.PENDING,
        ).values_list("project_id").annotate(total=Count("id")),
    )
    for project in projects:
        project.pending_count = pending_map.get(project.pk, 0)
    return render(request, "projects/mine.html", {
        "projects": projects,
        "counts": counts,
        "active_status": status,
        "filter_active": status != "all",
    })


@login_required
@require_GET
def detail(request, project_id):
    return render(request, "projects/detail.html", detail_context(request.user, project_id))
