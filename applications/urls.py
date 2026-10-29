from django.urls import path

from . import views

app_name = "applications"
urlpatterns = [
    path("applications/", views.mine, name="mine"),
    path("projects/<uuid:project_id>/apply/", views.submit, name="submit"),
]
