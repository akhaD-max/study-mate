from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.views.decorators.vary import vary_on_headers

from projects.models import Category, Project, ProjectRole


def home(request):
    """Главная страница ведёт пользователя сразу в каталог проектов."""
    return redirect("main:catalog")


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
