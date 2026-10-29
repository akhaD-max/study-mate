"""Middleware для проверки валидности сессии пользователя."""

from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()


class ValidateUserSessionMiddleware(MiddlewareMixin):
    """
    Проверяет, что пользователь в сессии всё ещё существует в БД.
    Если пользователь удалён — очищает сессию и делает запрос анонимным.
    """

    def process_request(self, request):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return

        # request.user уже загружен AuthenticationMiddleware
        # Проверяем, существует ли пользователь в БД
        user_pk = request.user.pk
        if user_pk is None:
            return

        # Используем exists() для эффективной проверки без загрузки объекта
        if not User.objects.filter(pk=user_pk).exists():
            # Пользователь удалён — флашим сессию
            request.session.flush()
            # request.user станет AnonymousUser на следующем цикле middleware
            # Но можно принудительно сбросить сейчас:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
