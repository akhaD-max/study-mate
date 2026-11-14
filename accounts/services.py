from django.db import transaction

from .models import User


@transaction.atomic
def update_profile(*, user, profile_data):
    """Атомарно обновить только профиль вошедшего пользователя."""
    profile = User.objects.select_for_update().get(pk=user.pk)
    fields = ("full_name", "university", "specialty", "course", "desired_role", "bio")
    for name in fields:
        setattr(profile, name, profile_data[name])
    profile.save(update_fields=fields)
    profile.skills.set(profile_data["skills"])
    return profile
