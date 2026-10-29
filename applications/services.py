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


def list_project_applications(*, user, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if not user.is_authenticated or project.author_id != user.pk:
        raise PermissionDenied("Управлять заявками может только руководитель проекта.")
    return project, project.applications.select_related("user", "role").order_by(
        "-created_at", "-pk",
    )


def review_application(*, user, application_id, accept):
    """Проект → роль → заявка: общий порядок блокировок с подачей и выходом."""
    candidate = get_object_or_404(Application, pk=application_id)
    with transaction.atomic():
        project = get_object_or_404(Project.objects.select_for_update(), pk=candidate.project_id)
        if not user.is_authenticated or project.author_id != user.pk:
            raise PermissionDenied("Рассматривать заявки может только руководитель проекта.")
        role = get_object_or_404(
            ProjectRole.objects.select_for_update(), pk=candidate.role_id, project=project,
        )
        application = get_object_or_404(
            Application.objects.select_for_update(), pk=application_id,
        )
        target = Application.Status.ACCEPTED if accept else Application.Status.REJECTED
        if application.status == target:
            return application
        if application.status != Application.Status.PENDING:
            raise ValidationError("Заявка уже рассмотрена. Обновите страницу.")
        if accept:
            role.project = project
            if not role.is_available:
                raise ValidationError("Роль закрыта или свободных мест больше нет.")
            if application.user_id == project.author_id:
                raise ValidationError("Руководитель уже состоит в проекте.")
            if ProjectMember.objects.filter(project=project, user_id=application.user_id).exists():
                raise ValidationError("Студент уже в команде проекта.")
            ProjectMember.objects.create(
                project=project, role=role, user_id=application.user_id,
            )
        application.status = target
        application.save(update_fields=["status", "updated_at"])
        return application


def withdraw_application(*, user, application_id):
    candidate = get_object_or_404(Application, pk=application_id)
    with transaction.atomic():
        get_object_or_404(Project.objects.select_for_update(), pk=candidate.project_id)
        application = get_object_or_404(
            Application.objects.select_for_update(), pk=application_id,
        )
        if not user.is_authenticated or application.user_id != user.pk:
            raise PermissionDenied("Можно отозвать только собственную заявку.")
        if application.status != Application.Status.PENDING:
            raise ValidationError("Можно отозвать только заявку на рассмотрении.")
        application.delete()


def leave_project(*, user, project_id):
    with transaction.atomic():
        project = get_object_or_404(Project.objects.select_for_update(), pk=project_id)
        if not user.is_authenticated or user.pk is None:
            raise PermissionDenied("Необходимо войти в аккаунт.")
        if project.author_id == user.pk:
            raise ValidationError("Руководитель не может покинуть свой проект.")
        membership = ProjectMember.objects.filter(project=project, user=user).first()
        if membership is None:
            return
        get_object_or_404(ProjectRole.objects.select_for_update(), pk=membership.role_id)
        membership.delete()
