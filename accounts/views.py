from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .decorators import session_required
from .forms import AuthenticationForm, ProfileForm, RegistrationForm
from .services import update_profile

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
                return auth_redirect(request, reverse("profiles:edit"))
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


@session_required
@require_GET
def own_profile(request):
    return redirect("profiles:detail", user_id=request.user.pk)


@session_required
@require_GET
def profile_detail(request, user_id):
    profile_user = get_object_or_404(
        User.objects.select_related("desired_role").prefetch_related("skills"),
        pk=user_id,
        is_active=True,
    )
    profile_is_empty = not any(
        (
            profile_user.university,
            profile_user.specialty,
            profile_user.course,
            profile_user.bio,
            profile_user.desired_role_id,
            profile_user.skills.all(),
        )
    )
    return render(
        request,
        "accounts/profile_detail.html",
        {
            "profile_user": profile_user,
            "is_owner": request.user.pk == profile_user.pk,
            "profile_is_empty": profile_is_empty,
        },
    )


@session_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    # URL не принимает ID редактируемого аккаунта: владелец определяется сессией.
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        profile = update_profile(user=request.user, profile_data=form.cleaned_data)
        messages.success(request, "Профиль успешно обновлён")
        return redirect("profiles:detail", user_id=profile.pk)
    return render(
        request,
        "accounts/profile_edit.html",
        {
            "form": form,
            "cancel_url": reverse(
                "profiles:detail", kwargs={"user_id": request.user.pk}
            ),
        },
    )
