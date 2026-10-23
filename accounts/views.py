from django.contrib.auth import get_user_model, login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RegistrationForm

User = get_user_model()

@require_http_methods(["GET", "POST"])
def register_page(request):

    if request.user.is_authenticated:
        return redirect("main:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                with transaction.atomic():
                    user = User.objects.create_user(email=email, password=password,)
            except IntegrityError:
                if not User.objects.filter(email__iexact=email).exists():
                    raise
                form.add_error("email", "Пользователь с таким email уже зарегистрирован",)
            else:
                login(request, user)
                return redirect("main:home")

    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form":form},)

def login_page(request):
    return render(request, "accounts/login.html")


def logout_page(request):
    return render(request, "accounts/logout.html")
