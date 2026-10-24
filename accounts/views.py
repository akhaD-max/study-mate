from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .forms import AuthenticationForm, RegistrationForm

User = get_user_model()


def auth_redirect(request, target):
    if request.headers.get("HX-Request") == "true":
        return HttpResponse(headers={"HX-Redirect": target})
    return redirect(target)


@require_http_methods(["GET", "POST"])
def register_page(request):
    if request.user.is_authenticated:
        return auth_redirect(request, reverse("main:home"))

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            try:
                with transaction.atomic():
                    user = User.objects.create_user(email=email, password=password)
            except IntegrityError:
                if not User.objects.filter(email__iexact=email).exists():
                    raise
                form.add_error(
                    "email", "Пользователь с таким email уже зарегистрирован."
                )
            else:
                login(request, user)
                return auth_redirect(request, reverse("main:home"))
    else:
        form = RegistrationForm()

    template = "accounts/register.html"
    if request.method == "POST" and request.headers.get("HX-Request") == "true":
        template = "accounts/partials/register_form.html"
    return render(request, template, {"form": form})


class LoginPageView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True
    next_page = "main:home"

    def get_template_names(self):
        if (
            self.request.method == "POST"
            and self.request.headers.get("HX-Request") == "true"
        ):
            return ["accounts/partials/login_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        response = super().form_valid(form)
        return auth_redirect(self.request, response.url)

    def get(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and request.user.is_authenticated:
            return auth_redirect(request, self.get_success_url())
        return super().get(request, *args, **kwargs)


@require_POST
def logout_page(request):
    logout(request)
    return redirect("main:catalog")
