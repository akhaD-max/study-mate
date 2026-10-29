from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("create/", views.create, name="create"),
    path("mine/", views.mine, name="mine"),
    path("<uuid:project_id>/", views.detail, name="detail"),
]
