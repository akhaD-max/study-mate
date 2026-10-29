from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from .forms import ProjectCreateForm, ProjectRoleFormSet
from .models import Project, ProjectRole


def create_project(*, author, title, description, category_id, roles) -> Project:
    """Проверить данные и атомарно опубликовать проект со всеми ролями."""
    if not author.is_authenticated or author.pk is None:
        raise PermissionDenied("Необходимо войти в аккаунт.")
    form = ProjectCreateForm({
        "title": title, "description": description, "category_id": category_id,
    })
    data = {"roles-TOTAL_FORMS": len(roles), "roles-INITIAL_FORMS": 0}
    for index, role in enumerate(roles):
        data.update({f"roles-{index}-{key}": value for key, value in role.items()})
    formset = ProjectRoleFormSet(data)
    valid_project = form.is_valid()
    valid_roles = formset.is_valid()
    if not valid_project or not valid_roles:
        errors = {key: list(value) for key, value in form.errors.items()}
        role_errors = list(formset.non_form_errors())
        for index, role_form in enumerate(formset):
            for messages in role_form.errors.values():
                role_errors.extend(f"Роль {index + 1}: {message}" for message in messages)
        if role_errors:
            errors["roles"] = role_errors
        raise ValidationError(errors)
    try:
        with transaction.atomic():
            project = Project.objects.create(
                author=author, title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                category=form.cleaned_data["category_id"], status=Project.Status.OPEN,
            )
            for role_form in formset:
                if role_form.cleaned_data:
                    ProjectRole.objects.create(project=project, **role_form.cleaned_data)
            return project
    except IntegrityError as error:
        diag = getattr(error.__cause__, "diag", None)
        if diag and diag.constraint_name == "projects_project_author_title_uniq":
            raise ValidationError({"title": "У вас уже есть проект с таким названием."}) from error
        raise
