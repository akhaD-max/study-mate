from django.urls import path

from . import views

app_name = "applications"
urlpatterns = [
    path("applications/", views.mine, name="mine"),
    path("applications/my/", views.mine, name="my"),
    path("projects/<uuid:project_id>/apply/", views.submit, name="submit"),
    path("projects/<uuid:project_id>/applications/", views.incoming, name="incoming"),
    path("applications/<uuid:application_id>/accept/", views.review,
         {"accept": True}, name="accept"),
    path("applications/<uuid:application_id>/reject/", views.review,
         {"accept": False}, name="reject"),
    path("applications/<uuid:application_id>/withdraw/", views.withdraw, name="withdraw"),
    path("projects/<uuid:project_id>/leave/", views.leave, name="leave"),
]
