from djoser.serializers import UserSerializer
from rest_framework import serializers

from users.models import Subscription, User


class CustomUserSerializer(UserSerializer):
    """Расширенный сериализатор пользователя с информацией о подписке."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("is_subscribed",)

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на данного пользователя.

        Args:
            obj: Объект пользователя

        Returns:
            bool: True если подписан, False иначе
        """
        request = self.context.get("request")

        # Если пользователь не аутентифицирован, возвращаем False
        if not request or not request.user.is_authenticated:
            return False

        # Проверяем наличие записи в модели Subscription
        return Subscription.objects.filter(user=request.user, author=obj).exists()
