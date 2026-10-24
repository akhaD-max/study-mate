import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from applications.models import Application
from projects.models import Category, Project, ProjectMember, ProjectRole

DEMO_PASSWORD_ENV_VARS = ("SEED_DEMO_PASSWORD", "DEMO_PASSWORD")
MIN_DEMO_PASSWORD_LENGTH = 6

DEMO_AUTHOR = {
    "email": "author@studymate.local",
    "full_name": "Алексей Морозов",
}
DEMO_STUDENTS = (
    {
        "email": "student1@studymate.local",
        "full_name": "Мария Соколова",
    },
    {
        "email": "student2@studymate.local",
        "full_name": "Дмитрий Волков",
    },
)

DEMO_CATEGORIES = (
    {"slug": "development", "name": "Разработка"},
    {"slug": "science", "name": "Наука"},
    {"slug": "design", "name": "Дизайн"},
)


def _resolve_password(cli_password: str | None) -> str:
    raw = cli_password
    if raw is None:
        for env_name in DEMO_PASSWORD_ENV_VARS:
            candidate = os.environ.get(env_name)
            if candidate:
                raw = candidate
                break

    if not raw or not raw.strip():
        env_names = " / ".join(DEMO_PASSWORD_ENV_VARS)
        raise CommandError(
            "Не задан пароль демо-пользователей. Передайте аргумент "
            f"--password или переменную окружения {env_names}."
        )

    if len(raw) < MIN_DEMO_PASSWORD_LENGTH:
        raise CommandError(
            "Пароль демо-пользователей должен содержать минимум "
            f"{MIN_DEMO_PASSWORD_LENGTH} символов."
        )
    return raw


def _ensure_demo_user(*, email: str, full_name: str, password: str):
    user_model = get_user_model()
    lookup_email = email.strip().lower()
    defaults = {"full_name": full_name}
    if user_model.USERNAME_FIELD != "email":
        defaults[user_model.USERNAME_FIELD] = lookup_email

    user, created = user_model.objects.get_or_create(
        email=lookup_email,
        defaults=defaults,
    )
    if created or not user.check_password(password):
        user.set_password(password)
        user.save(update_fields=["password"])
    return user, created


def _ensure_sample_application(
    *,
    user,
    project: Project,
    role: ProjectRole,
    status: str,
    comment: str,
) -> tuple[Application | None, bool]:
    # Не перезаписываем и не сбрасываем существующие заявки по проекту.
    existing = Application.objects.filter(project=project, user=user).first()
    if existing is not None:
        return existing, False

    application = Application.objects.create(
        user=user,
        project=project,
        role=role,
        status=status,
        comment=comment,
    )
    return application, True


class Command(BaseCommand):
    help = (
        "Создаёт идемпотентные демонстрационные данные для сценария 4-го спринта "
        "(пользователи, направления, проекты, роли, членство и образцы заявок)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            dest="password",
            default=None,
            help=(
                "Пароль для демо-аккаунтов (по умолчанию берётся из "
                "SEED_DEMO_PASSWORD или DEMO_PASSWORD)."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = _resolve_password(options.get("password"))

        author, _ = _ensure_demo_user(
            email=DEMO_AUTHOR["email"],
            full_name=DEMO_AUTHOR["full_name"],
            password=password,
        )
        student_one, _ = _ensure_demo_user(
            email=DEMO_STUDENTS[0]["email"],
            full_name=DEMO_STUDENTS[0]["full_name"],
            password=password,
        )
        student_two, _ = _ensure_demo_user(
            email=DEMO_STUDENTS[1]["email"],
            full_name=DEMO_STUDENTS[1]["full_name"],
            password=password,
        )

        categories: dict[str, Category] = {}
        for item in DEMO_CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=item["slug"],
                defaults={"name": item["name"]},
            )
            categories[item["slug"]] = category

        # Проект 1: основной открытый проект с тремя ролями под все проверки карточки:
        # свободная роль, полностью занятая роль и закрытая роль.
        main_project, _ = Project.objects.get_or_create(
            author=author,
            title="Платформа учебных команд StudyMate",
            defaults={
                "category": categories["development"],
                "description": (
                    "Веб-платформа для поиска студенческих команд, откликов на роли "
                    "и сопровождения семестровых проектов."
                ),
                "status": Project.Status.OPEN,
            },
        )
        free_role, _ = ProjectRole.objects.get_or_create(
            project=main_project,
            name="Backend-разработчик",
            defaults={
                "description": "Разработка серверной логики на Django и PostgreSQL.",
                "capacity": 2,
                "is_open": True,
            },
        )
        occupied_role, _ = ProjectRole.objects.get_or_create(
            project=main_project,
            name="Frontend-разработчик",
            defaults={
                "description": "Верстка шаблонов и интерактивных фрагментов на HTMX.",
                "capacity": 1,
                "is_open": True,
            },
        )
        closed_role, _ = ProjectRole.objects.get_or_create(
            project=main_project,
            name="UI/UX дизайнер",
            defaults={
                "description": "Подготовка макетов карточек и состояний форм.",
                "capacity": 2,
                "is_open": False,
            },
        )
        ProjectMember.objects.get_or_create(
            project=main_project,
            user=student_two,
            defaults={"role": occupied_role},
        )

        # Проект 2: у первого студента уже есть активная заявка (pending) —
        # для проверки запрета повторного активного отклика на тот же проект.
        duplicate_project, _ = Project.objects.get_or_create(
            author=author,
            title="Телеграм-бот расписания и дедлайнов",
            defaults={
                "category": categories["development"],
                "description": (
                    "Сервис напоминаний о занятиях, контрольных точках "
                    "и командных встречах."
                ),
                "status": Project.Status.OPEN,
            },
        )
        bot_python_role, _ = ProjectRole.objects.get_or_create(
            project=duplicate_project,
            name="Python-разработчик",
            defaults={
                "description": "Интеграция с расписанием и хранение подписок.",
                "capacity": 2,
                "is_open": True,
            },
        )
        ProjectRole.objects.get_or_create(
            project=duplicate_project,
            name="QA-инженер",
            defaults={
                "description": (
                    "Тестирование сценариев уведомлений и граничных случаев."
                ),
                "capacity": 1,
                "is_open": True,
            },
        )
        _ensure_sample_application(
            user=student_one,
            project=duplicate_project,
            role=bot_python_role,
            status=Application.Status.PENDING,
            comment="Писал ботов на Python и работал с PostgreSQL.",
        )

        # Проект 3: проект в работе (набор закрыт) + образец принятой заявки.
        in_progress_project, _ = Project.objects.get_or_create(
            author=author,
            title="Аналитика вовлечённости онлайн-курсов",
            defaults={
                "category": categories["science"],
                "description": (
                    "Исследование учебных траекторий и прогнозирование "
                    "успешной сдачи курса."
                ),
                "status": Project.Status.IN_PROGRESS,
            },
        )
        analyst_role, _ = ProjectRole.objects.get_or_create(
            project=in_progress_project,
            name="Data Analyst",
            defaults={
                "description": "Подготовка выборок, визуализация метрик и выводов.",
                "capacity": 2,
                "is_open": True,
            },
        )
        ProjectMember.objects.get_or_create(
            project=in_progress_project,
            user=student_one,
            defaults={"role": analyst_role},
        )
        _ensure_sample_application(
            user=student_one,
            project=in_progress_project,
            role=analyst_role,
            status=Application.Status.ACCEPTED,
            comment="Готова взять расчёт метрик и отчёт по выборке.",
        )

        # Проект 4: образец отклонённой заявки у первого студента и активная
        # заявка второго студента (проверка статусов и изоляции чужих заявок).
        design_project, _ = Project.objects.get_or_create(
            author=author,
            title="Дизайн-система студенческих сервисов",
            defaults={
                "category": categories["design"],
                "description": (
                    "Единая библиотека компонентов, сеток и состояний интерфейса."
                ),
                "status": Project.Status.OPEN,
            },
        )
        designer_role, _ = ProjectRole.objects.get_or_create(
            project=design_project,
            name="Продуктовый дизайнер",
            defaults={
                "description": "Проектирование пользовательских сценариев и UI-кита.",
                "capacity": 2,
                "is_open": True,
            },
        )
        _ensure_sample_application(
            user=student_one,
            project=design_project,
            role=designer_role,
            status=Application.Status.REJECTED,
            comment="Хотела бы поработать над компонентами форм.",
        )
        _ensure_sample_application(
            user=student_two,
            project=design_project,
            role=designer_role,
            status=Application.Status.PENDING,
            comment="Могу помочь с компонентной библиотекой.",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Демонстрационные данные готовы: "
                f"автор={author.email}, "
                f"студенты=({student_one.email}, {student_two.email}), "
                f"проектов={Project.objects.filter(author=author).count()} "
                f"(свободная роль: «{free_role.name}», "
                f"занятая: «{occupied_role.name}», "
                f"закрытая: «{closed_role.name}»)."
            )
        )
