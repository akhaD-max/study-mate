import uuid
from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email(email):
    """Убираю пробелы по краям и привожу email к нижнему регистру."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email or not email.strip():
            raise ValueError("Email обязателен.")
        user = self.model(email=normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("У суперпользователя is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        # Ищу по email без учёта регистра.
        email = normalize_email(username)
        return self.get(**{self.model.USERNAME_FIELD: email})


class Skill(models.Model):
    """Общий справочник навыков студентов и будущих требований проектов."""

    class Category(models.TextChoices):
        HARD = "hard", "Профессиональные навыки"
        SOFT = "soft", "Гибкие навыки"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Навык", max_length=100)
    category = models.CharField("Категория", max_length=4, choices=Category.choices)
    is_active = models.BooleanField("Доступен для выбора", default=True)

    class Meta:
        verbose_name = "навык"
        verbose_name_plural = "навыки"
        ordering: ClassVar[list[str]] = ["category", "name"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                Lower("name"), name="accounts_skill_name_ci_unique"
            ),
        ]

    def __str__(self):
        return self.name


class Specialization(models.Model):
    """Предпочтение студента, не связанное с правами или ролью в проекте."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField("Код", unique=True, max_length=50)
    name = models.CharField("Специализация", max_length=100)
    is_active = models.BooleanField("Доступна для выбора", default=True)

    class Meta:
        verbose_name = "специализация"
        verbose_name_plural = "специализации"
        ordering: ClassVar[list[str]] = ["name"]

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email", unique=True)
    full_name = models.CharField("ФИО", max_length=150, blank=True, default="")
    university = models.CharField("Вуз", max_length=200, blank=True, default="")
    specialty = models.CharField(
        "Специальность", max_length=200, blank=True, default=""
    )
    course = models.PositiveSmallIntegerField(
        "Курс",
        null=True,
        blank=True,
        choices=[(number, str(number)) for number in range(1, 7)],
        validators=[MinValueValidator(1), MaxValueValidator(6)],
    )
    bio = models.TextField("О себе", max_length=1000, blank=True, default="")
    desired_role = models.ForeignKey(
        Specialization,
        verbose_name="Желаемая роль",
        on_delete=models.SET_NULL,
        related_name="students",
        null=True,
        blank=True,
    )
    skills = models.ManyToManyField(
        Skill, verbose_name="Навыки", related_name="students", blank=True
    )
    is_active = models.BooleanField("активен", default=True)
    is_staff = models.BooleanField("доступ в админку", default=False)
    date_joined = models.DateTimeField("дата регистрации", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        ordering: ClassVar[list[str]] = ["email"]
        constraints: ClassVar[list] = [
            # unique=True проверяет формы, Lower держит регистр в БД.
            models.UniqueConstraint(
                Lower("email"), name="accounts_user_email_ci_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(course__isnull=True)
                | models.Q(course__range=(1, 6)),
                name="accounts_user_course_range",
            ),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or "Студент"

    def get_short_name(self):
        return self.get_full_name()
