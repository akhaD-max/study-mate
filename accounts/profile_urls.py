from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.own_profile, name="self"),
    path("edit/", views.profile_edit, name="edit"),
    path("<uuid:user_id>/", views.profile_detail, name="detail"),
]
