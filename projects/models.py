import uuid
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("название", max_length=100, unique=True)
    slug = models.SlugField(
        "слаг",
        max_length=100,
        unique=True,
        allow_unicode=True,
        blank=True,
    )

    class Meta:
        verbose_name = "направление"
        verbose_name_plural = "направления"
        ordering: ClassVar[list[str]] = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("name"),
                name="projects_category_name_ci_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="projects_category_name_non_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        if not self.slug:
            generated = slugify(self.name, allow_unicode=True)
            self.slug = generated or str(self.id)[:8]
        super().save(*args, **kwargs)


class Project(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        IN_PROGRESS = "in_progress", "В работе"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authored_projects",
        verbose_name="автор",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name="направление",
    )
    title = models.CharField("название", max_length=100)
    description = models.TextField("описание", max_length=5000, blank=True, default="")
    status = models.CharField(
        "статус набора",
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField("создан", auto_now_add=True)
    updated_at = models.DateTimeField("обновлён", auto_now=True)

    class Meta:
        verbose_name = "проект"
        verbose_name_plural = "проекты"
        ordering: ClassVar[list[str]] = ["-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["author", "title"],
                name="projects_project_author_title_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["open", "in_progress", "completed", "cancelled"],
                ),
                name="projects_project_status_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["status", "-created_at"],
                name="proj_status_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class ProjectRoleQuerySet(models.QuerySet):
    def with_occupancy(self):
        return self.annotate(
            _occupied_count=models.Count("memberships", distinct=True),
        )


class ProjectRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="roles",
        verbose_name="проект",
    )
    name = models.CharField("название роли", max_length=100)
    description = models.TextField("описание роли", blank=True, default="")
    capacity = models.PositiveSmallIntegerField(
        "вместимость",
        validators=[MinValueValidator(1)],
    )
    is_open = models.BooleanField("набор открыт", default=True)
    created_at = models.DateTimeField("создана", auto_now_add=True)

    objects = ProjectRoleQuerySet.as_manager()

    class Meta:
        verbose_name = "роль проекта"
        verbose_name_plural = "роли проекта"
        ordering: ClassVar[list[str]] = ["created_at", "name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["project", "name"],
                name="projects_role_project_name_uniq",
            ),
            # Нужен для FK проверки принадлежности роли проекту в PostgreSQL.
            models.UniqueConstraint(
                fields=["id", "project"],
                name="projects_role_id_project_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="projects_role_capacity_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.title} — {self.name}"

    @property
    def occupied_places(self) -> int:
        if "_occupied_count" in self.__dict__:
            return self._occupied_count
        if self._state.adding:
            return 0
        return self.memberships.count()

    @property
    def free_places(self) -> int:
        if not self.capacity:
            return 0
        return max(self.capacity - self.occupied_places, 0)

    @property
    def is_available(self) -> bool:
        if not self.project_id:
            return False
        return bool(
            self.is_open
            and self.free_places > 0
            and self.project.status == Project.Status.OPEN
        )

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        self.__dict__.pop("_occupied_count", None)
        return super().refresh_from_db(
            using=using,
            fields=fields,
            from_queryset=from_queryset,
        )

    def clean(self):
        super().clean()
        if not self._state.adding and self.capacity is not None:
            occupied = self.memberships.count()
            if self.capacity < occupied:
                raise ValidationError(
                    {
                        "capacity": (
                            f"Вместимость ({self.capacity}) не может быть меньше "
                            f"числа принятых участников ({occupied})."
                        )
                    }
                )


class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="проект",
    )
    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.RESTRICT,
        related_name="memberships",
        verbose_name="роль",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        verbose_name="участник",
    )
    joined_at = models.DateTimeField("вступил", auto_now_add=True)

    class Meta:
        verbose_name = "участник проекта"
        verbose_name_plural = "участники проекта"
        ordering: ClassVar[list[str]] = ["joined_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="projects_member_project_user_uniq",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["role", "user"],
                name="proj_member_role_user_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.role.name} ({self.project.title})"

    def clean(self):
        super().clean()
        if self.role_id and self.project_id and self.role.project_id != self.project_id:
            raise ValidationError(
                {"role": "Выбранная роль не принадлежит указанному проекту."}
            )
