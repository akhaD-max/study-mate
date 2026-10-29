from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from projects.models import Project, ProjectMember, ProjectRole

from .models import Application


def application_block_reason(project, user_id):
    if project.author_id == user_id:
        return "Нельзя подать заявку на собственный проект."
    if ProjectMember.objects.filter(project=project, user_id=user_id).exists():
        return "Вы уже в команде проекта."
    if Application.objects.filter(
        project=project, user_id=user_id, status=Application.Status.PENDING,
    ).exists():
        return "Заявка на этот проект уже отправлена."
    if project.status != Project.Status.OPEN:
        return "Набор в проект закрыт."
    return ""


def submit_application(*, user, project_id, role_id, comment=""):
    if not user.is_authenticated or user.pk is None:
        raise PermissionDenied("Необходимо войти в аккаунт.")
    if len(comment) > 300:
        raise ValidationError("Письмо должно содержать не более 300 символов.")
    with transaction.atomic():
        # Все операции изменения набора/состава должны блокировать проект,
        # затем роль в этом же порядке.
        project = get_object_or_404(Project.objects.select_for_update(), pk=project_id)
        reason = application_block_reason(project, user.pk)
        if reason:
            raise ValidationError(reason)
        try:
            role = ProjectRole.objects.select_for_update().get(pk=role_id, project=project)
        except (ProjectRole.DoesNotExist, ValidationError, ValueError, TypeError):
            raise ValidationError("Роль не принадлежит этому проекту.") from None
        role.project = project
        if not role.is_available:
            raise ValidationError("Роль закрыта или свободных мест больше нет.")
        try:
            with transaction.atomic():
                return Application.objects.create(
                    user=user, project=project, role=role, comment=comment,
                )
        except IntegrityError as error:
            if getattr(error.__cause__, "diag", None) and (
                error.__cause__.diag.constraint_name == "applications_active_per_project_uniq"
            ):
                raise ValidationError("Заявка на этот проект уже отправлена.") from error
            raise


def list_my_applications(user):
    return Application.objects.filter(user=user).select_related(
        "project", "role",
    ).order_by("-created_at", "-pk")
