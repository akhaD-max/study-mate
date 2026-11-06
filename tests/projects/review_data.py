"""Данные приёмки Sprint 6; не импортировать при обычном запуске приложения.

Обе функции предназначены для отдельной тестовой БД. Данные соответствуют
`docs/sprint-6/catalog-test-cases.md`; наборы P01–P10 и Q01–Q13 не смешиваются.
Вызовов на import нет. Пароль обязательен и не имеет значения по умолчанию.
"""

from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.db import transaction

from applications.models import Application
from projects.models import Category, Project, ProjectMember, ProjectRole


@transaction.atomic
def seed_empty_review_catalog(*, password):
    """Наполнить пустую БД набором P01–P10, вернуть проекты по их QA-ID."""
    if not password or len(password) < 6:
        raise ValueError("Для локальных демо-аккаунтов нужен пароль от 6 символов.")
    if Project.objects.exists() or get_user_model().objects.exists() or Category.objects.exists():
        raise ValueError("Набор P01–P10 создаётся только в пустой пользовательской БД.")

    user_model = get_user_model()
    author = user_model.objects.create_user(
        "review-author@studymate.local", password, full_name="Руководитель приёмки",
    )
    students = [
        user_model.objects.create_user(
            f"review-student{number}@studymate.local", password,
            full_name=f"Студент приёмки {number}",
        )
        for number in range(1, 5)
    ]
    development = Category.objects.create(name="Разработка", slug="development")
    design = Category.objects.create(name="Дизайн", slug="design")
    science = Category.objects.create(name="Наука", slug="science")
    specifications = [
        ("P01", "Python Lab", development, "open", [("Backend", 2, True)]),
        ("P02", "Python Full", development, "open", [("Backend", 1, True)]),
        ("P03", "Python Closed Role", development, "open", [("Backend", 2, False)]),
        ("P04", "Python Course", development, "in_progress", [("Backend", 2, True)]),
        ("P05", "Python Mixed", development, "open", [
            ("Backend", 1, True), ("Frontend", 1, False),
        ]),
        ("P06", "Python No Roles", development, "open", []),
        ("P07", "User Research", design, "open", [("UX", 2, True)]),
        ("P08", "Робот помощник", science, "open", [("Исследователь", 1, True)]),
        ("P09", "Python Archive", development, "completed", [("Backend", 1, True)]),
        ("P10", "Python Cancelled", development, "cancelled", [("Backend", 1, True)]),
    ]
    projects = {}
    for key, title, category, status, roles in specifications:
        project = Project.objects.create(
            author=author, category=category, title=title, status=status,
            description=(
                "Исследование интерфейсов Python Lab"
                if key == "P07" else "Учебный проект для приёмки каталога."
            ),
        )
        projects[key] = project
        for name, capacity, is_open in roles:
            role = ProjectRole.objects.create(
                project=project, name=name, capacity=capacity, is_open=is_open,
            )
            if key in {"P01", "P02"} or (key == "P05" and name == "Backend"):
                ProjectMember.objects.create(project=project, role=role, user=students[0])
        if key in {"P01", "P07", "P08"}:
            day = {"P01": 1, "P07": 2, "P08": 3}[key]
            Project.objects.filter(pk=project.pk).update(
                created_at=datetime(2026, 11, day, 12, tzinfo=UTC),
            )
    for student in students[1:3]:
        Application.objects.create(
            project=projects["P01"], role=projects["P01"].roles.get(name="Backend"),
            user=student, comment="Тестовая заявка: не занимает место.",
        )
    return projects


@transaction.atomic
def seed_empty_pagination_catalog(*, password):
    """Наполнить другую пустую БД тринадцатью проектами Q01–Q13."""
    if not password or len(password) < 6:
        raise ValueError("Для локальных демо-аккаунтов нужен пароль от 6 символов.")
    if Project.objects.exists() or get_user_model().objects.exists() or Category.objects.exists():
        raise ValueError("Набор Q01–Q13 создаётся только в пустой пользовательской БД.")
    author = get_user_model().objects.create_user(
        "pagination@studymate.local", password, full_name="Автор пагинации",
    )
    category = Category.objects.create(name="Разработка", slug="development")
    projects = []
    for number in range(1, 14):
        project = Project.objects.create(
            author=author, category=category, title=f"Q{number:02d} Python",
        )
        ProjectRole.objects.create(project=project, name="Backend", capacity=1)
        Project.objects.filter(pk=project.pk).update(
            created_at=datetime(2026, 11, number, 12, tzinfo=UTC),
        )
        projects.append(project)
    return projects
