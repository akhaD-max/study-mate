import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        ACCEPTED = "accepted", "Принята"
        REJECTED = "rejected", "Отклонена"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="пользователь",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="проект",
    )
    role = models.ForeignKey(
        "projects.ProjectRole",
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="роль",
    )
    comment = models.CharField(
        "сопроводительное письмо",
        max_length=300,
        blank=True,
        default="",
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField("создана", auto_now_add=True)
    updated_at = models.DateTimeField("обновлена", auto_now=True)

    class Meta:
        verbose_name = "заявка"
        verbose_name_plural = "заявки"
        ordering: ClassVar[list[str]] = ["-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(status="pending"),
                name="applications_active_per_project_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "accepted", "rejected"],
                ),
                name="applications_app_status_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["user", "-created_at"],
                name="app_user_created_idx",
            ),
            models.Index(
                fields=["role", "status"],
                name="app_role_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.project.title} ({self.role.name})"
