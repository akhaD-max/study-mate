from django.shortcuts import redirect, render


PROJECT_DIRECTIONS = (
    ("", "Все направления"),
    ("development", "Разработка"),
    ("design", "Дизайн"),
    ("marketing", "Маркетинг"),
    ("science", "Наука"),
)


def home(request):
    """Главная страница ведёт пользователя сразу в каталог проектов."""
    return redirect("main:catalog")


def catalog(request):
    """Показывает каталог; подключение доменной модели проектов — следующий этап."""
    selected_direction = request.GET.get("direction", "")
    context = {
        "projects": [],
        "directions": PROJECT_DIRECTIONS,
        "selected_direction": selected_direction,
        "search_query": request.GET.get("q", ""),
        "sort": request.GET.get("sort", "newest"),
    }
    return render(request, "projects/catalog.html", context)
