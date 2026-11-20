# ruff: noqa: RUF012
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_catalogs"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectrole",
            name="required_skills",
            field=models.ManyToManyField(
                blank=True, related_name="project_roles", to="accounts.skill",
                verbose_name="требуемые навыки",
            ),
        ),
    ]
