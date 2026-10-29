from django.shortcuts import redirect

# Старое имя используется существующими ссылками; обработчик каталога один.
from projects.views import catalog

__all__ = ["catalog", "home"]


def home(request):
    return redirect("projects:catalog")
