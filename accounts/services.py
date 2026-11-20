from django.db import transaction

from .models import User

PROFILE_FIELDS = (
    "full_name",
    "university",
    "specialty",
    "education_status",
    "education_level",
    "course",
    "desired_role",
    "bio",
)


@transaction.atomic
def update_profile(*, user, profile_data):
    """Атомарно обновить только профиль вошедшего пользователя."""
    profile = User.objects.select_for_update().get(pk=user.pk)
    for name in PROFILE_FIELDS:
        setattr(profile, name, profile_data[name])
    profile.save(update_fields=PROFILE_FIELDS)
    profile.skills.set(profile_data["skills"])
    return profile
