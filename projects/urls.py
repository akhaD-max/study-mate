from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("<uuid:project_id>/", views.detail, name="detail"),
]
