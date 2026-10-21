from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError

from projects.selectors import get_project

from .storage import Application, get_store


def application_block_reason(store, project, student_id):
    if str(project.author_id) == student_id:
        return "Нельзя подать заявку на собственный проект."
    if (project.id, student_id) in store.memberships:
        return "Вы уже в команде проекта."
    if any(
        a.project.id == project.id and a.student_id == student_id
        and a.status in {"pending", "accepted"}
        for a in store.applications
    ):
        return "Заявка на этот проект уже отправлена."
    if project.status != "open":
        return "Набор в проект закрыт."
    return ""


def submit_application(*, user, project_id, role_id, comment=""):
    if not user.is_authenticated or user.pk is None:
        raise PermissionDenied("Необходимо войти в аккаунт.")
    if len(comment) > 300:
        raise ValidationError("Письмо должно содержать не более 300 символов.")
    store = get_store()
    # The complete check-and-create operation is atomic within this demo process.
    with store.lock:
        project = get_project(project_id)
        reason = application_block_reason(store, project, str(user.pk))
        if reason:
            raise ValidationError(reason)
        try:
            role = store.roles.get(UUID(str(role_id)))
        except (ValueError, TypeError, AttributeError):
            role = None
        if role is None or role.project_id != project.id:
            raise ValidationError("Роль не принадлежит этому проекту.")
        if not role.is_available:
            raise ValidationError("Роль закрыта или свободных мест больше нет.")
        application = Application(str(user.pk), project, role, comment)
        store.applications.append(application)
        return application


def list_my_applications(user):
    store = get_store()
    with store.lock:
        return sorted(
            (a for a in store.applications if a.student_id == str(user.pk)),
            key=lambda a: (a.created_at, a.id), reverse=True,
        )
