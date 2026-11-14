from django.db.models import Case, CharField, Exists, OuterRef, Q, Subquery, Value, When

from projects.models import Project, ProjectMember


def profile_projects(*, user_id, is_owner):
    """Реальное участие и авторство; чужой профиль не раскрывает открытые проекты."""
    membership = ProjectMember.objects.filter(
        project_id=OuterRef("pk"), user_id=user_id
    )
    projects = Project.objects.filter(Q(author_id=user_id) | Q(Exists(membership)))
    if not is_owner:
        projects = projects.filter(
            status__in=(Project.Status.IN_PROGRESS, Project.Status.COMPLETED)
        )
    return projects.annotate(
        profile_role=Case(
            When(author_id=user_id, then=Value("Автор проекта")),
            default=Subquery(membership.values("role__name")[:1]),
            output_field=CharField(),
        ),
    ).order_by("-created_at", "pk")
