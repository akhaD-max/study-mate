from django.urls import include, path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", include("accounts.profile_urls")),
    path("register/", views.register_page, name="register"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.logout_page, name="logout"),
]
