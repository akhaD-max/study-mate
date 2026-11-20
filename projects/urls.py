from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("create/", views.create, name="create"),
    path("mine/", views.mine, name="mine"),
    path("<uuid:project_id>/roles/<uuid:role_id>/skills/", views.edit_role_skills,
         name="edit_role_skills"),
    path("<uuid:project_id>/", views.detail, name="detail"),
]
