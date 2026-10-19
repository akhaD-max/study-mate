from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


def register_page(request):
    return render(request, "accounts/register.html")


def login_page(request):
    return render(request, "accounts/login.html")


@require_POST
def logout_page(request):
    logout(request)
    return redirect("main:catalog")
