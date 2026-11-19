from django.db import migrations

SPECIALIZATIONS = (
    ("backend", "Backend-разработчик"),
    ("frontend", "Frontend-разработчик"),
    ("fullstack", "Fullstack-разработчик"),
    ("mobile", "Мобильный разработчик"),
    ("gamedev", "Разработчик игр"),
    ("qa", "Тестировщик / QA"),
    ("system-analyst", "Системный аналитик"),
    ("business-analyst", "Бизнес-аналитик"),
    ("data-analyst", "Аналитик данных"),
    ("ml", "ML-разработчик"),
    ("ui-ux", "UI/UX-дизайнер"),
    ("graphic-design", "Графический дизайнер"),
    ("3d-design", "3D-дизайнер"),
    ("devops", "DevOps-инженер"),
    ("security", "Специалист по информационной безопасности"),
    ("marketing", "Маркетолог"),
    ("content", "Автор контента / редактор"),
    ("research", "Исследователь"),
)

HARD_SKILLS = (
    "Python",
    "Django",
    "SQL",
    "PostgreSQL",
    "Git",
    "Docker",
    "HTML",
    "CSS",
    "JavaScript",
    "TypeScript",
    "Java",
    "C#",
    "C++",
    "Kotlin",
    "Swift",
    "Unity",
    "Тестирование",
    "Анализ требований",
    "Анализ данных",
    "Машинное обучение",
    "Figma",
    "UI/UX-дизайн",
    "Графический дизайн",
    "3D-моделирование",
    "Linux",
    "Информационная безопасность",
    "Маркетинг",
    "Редактирование текстов",
    "Исследования",
)

SOFT_SKILLS = (
    "Работа в команде",
    "Коммуникация",
    "Критическое мышление",
    "Решение проблем",
    "Самоорганизация",
    "Готовность учиться",
)


def seed_profile_catalogs(apps, schema_editor):
    """Стартовые значения без изменения существующих профилей и прав."""
    database = schema_editor.connection.alias
    specialization = apps.get_model("accounts", "Specialization")
    skill = apps.get_model("accounts", "Skill")
    for code, name in SPECIALIZATIONS:
        specialization.objects.using(database).get_or_create(
            code=code,
            defaults={"name": name},
        )
    for category, names in (("hard", HARD_SKILLS), ("soft", SOFT_SKILLS)):
        for name in names:
            skill.objects.using(database).get_or_create(
                name__iexact=name,
                defaults={"name": name, "category": category},
            )


class Migration(migrations.Migration):
    dependencies = (("accounts", "0002_profile_fields"),)
    operations = (
        migrations.RunPython(
            seed_profile_catalogs, reverse_code=migrations.RunPython.noop
        ),
    )
