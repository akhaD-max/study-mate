from django.urls import include, path

urlpatterns = [
    path("projects/", include("projects.urls")),
    path("", include("applications.urls")),
    path("", include("config.urls")),
]
