from django.shortcuts import get_object_or_404

from .models import Project, ProjectRole


def list_projects():
    return Project.objects.filter(status=Project.Status.OPEN).select_related("author", "category")


def get_project(project_id):
    return get_object_or_404(Project.objects.select_related("author", "category"), pk=project_id)


def list_roles(project_id):
    return ProjectRole.objects.filter(project_id=project_id).select_related("project").with_occupancy()
