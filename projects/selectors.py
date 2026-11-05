from django.db.models import Count, Exists, F, Min, OuterRef, Prefetch, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from .models import Category, Project, ProjectRole


def list_categories():
    return Category.objects.order_by("name", "pk")


def list_projects():
    return Project.objects.filter(status=Project.Status.OPEN).select_related("author", "category")


def get_project(project_id):
    return get_object_or_404(Project.objects.select_related("author", "category"), pk=project_id)


def list_roles(project_id):
    return ProjectRole.objects.filter(project_id=project_id).select_related("project").with_occupancy()


def list_catalog_role_names():
    """Общий список должностей без нового справочника и без UUID отдельной вакансии.

    ProjectRole принадлежит одному проекту. Группируем одинаковые названия
    без учёта регистра, чтобы «Backend» не повторялся для каждого проекта.
    Min выбирает одно стабильное написание для подписи в select.
    """
    return (
        ProjectRole.objects.order_by()
        .annotate(role_key=Lower("name"))
        .values("role_key")
        .annotate(label=Min("name"))
        .order_by("role_key")
        .values_list("label", flat=True)
    )


def catalog_projects(*, q="", direction="", role="", open_only=True, sort="newest"):
    """Все условия применяются в PostgreSQL до пагинации.

    EXISTS проверяет одну и ту же роль: она должна иметь нужное название,
    открытый набор и место. Иначе проект с полной ролью Backend и свободной
    ролью Designer ошибочно попал бы в поиск доступных Backend-вакансий.
    EXISTS также не размножает карточки, когда подходят несколько ролей.
    """
    matching_roles = ProjectRole.objects.filter(project_id=OuterRef("pk"))
    if role:
        matching_roles = matching_roles.filter(name__iexact=role)
    if open_only:
        matching_roles = (
            matching_roles.filter(is_open=True).order_by().with_occupancy()
            .filter(capacity__gt=F("_occupied_count"))
        )

    projects = Project.objects.all()
    if open_only:
        projects = projects.filter(status=Project.Status.OPEN)
    if role or open_only:
        projects = projects.filter(Exists(matching_roles))
    if direction:
        projects = projects.filter(category__slug=direction)
    if q:
        projects = projects.filter(Q(title__icontains=q) | Q(description__icontains=q))

    ordering = {
        "newest": ("-created_at", "pk"),
        "oldest": ("created_at", "pk"),
        "members": ("-member_count", "-created_at", "pk"),
        "fewer_members": ("member_count", "-created_at", "pk"),
    }
    return (
        projects.select_related("category", "author")
        .annotate(member_count=Count("memberships", distinct=True))
        .prefetch_related(Prefetch(
            "roles", queryset=ProjectRole.objects.filter(is_open=True).with_occupancy(),
            to_attr="catalog_roles",
        ))
        .order_by(*ordering[sort])
    )
