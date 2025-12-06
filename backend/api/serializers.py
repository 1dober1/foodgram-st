from base64 import b64decode

from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
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


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ("id", "name", "color", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для связки рецепта и ингредиента с количеством."""

    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name")
    measurement_unit = serializers.CharField(source="ingredient.measurement_unit")
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = RecipeIngredientSerializer(source="recipeingredient_set", many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        """Проверяет, добавлен ли рецепт в избранное текущим пользователем."""
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, добавлен ли рецепт в корзину текущим пользователем."""
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта для ответов action'ов (избранное, корзина)."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class Base64ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображений в формате Base64."""

    def to_internal_value(self, data):
        """Декодирует строку base64 в файл Django."""
        if isinstance(data, str) and data.startswith("data:image"):
            # Извлекаем base64 часть из data URL формата
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(b64decode(imgstr), name=f"image.{ext}")

        return super().to_internal_value(data)


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Сериализатор для ингредиентов при записи рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("ingredients", "tags", "image", "name", "text", "cooking_time")

    def create(self, validated_data):
        """Создает новый рецепт с ингредиентами и тегами."""
        # Извлекаем ingredients и tags из validated_data
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")

        # Создаем рецепт с текущим пользователем как автор
        validated_data["author"] = self.context["request"].user
        recipe = Recipe.objects.create(**validated_data)

        # Устанавливаем теги
        recipe.tags.set(tags_data)

        # Создаем ингредиенты через bulk_create
        recipe_ingredients = []
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(id=ingredient_data["id"])
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=ingredient_data["amount"],
                )
            )

        RecipeIngredient.objects.bulk_create(recipe_ingredients)

        return recipe

    def update(self, instance, validated_data):
        """Обновляет существующий рецепт."""
        # Извлекаем ingredients и tags из validated_data
        ingredients_data = validated_data.pop("ingredients", None)
        tags_data = validated_data.pop("tags", None)

        # Обновляем основные поля рецепта
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Если переданы теги, обновляем их
        if tags_data is not None:
            instance.tags.set(tags_data)

        # Если переданы ингредиенты, обновляем их
        if ingredients_data is not None:
            # Удаляем старые связи ингредиентов
            RecipeIngredient.objects.filter(recipe=instance).delete()

            # Создаем новые ингредиенты через bulk_create
            recipe_ingredients = []
            for ingredient_data in ingredients_data:
                ingredient = Ingredient.objects.get(id=ingredient_data["id"])
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=instance,
                        ingredient=ingredient,
                        amount=ingredient_data["amount"],
                    )
                )

            RecipeIngredient.objects.bulk_create(recipe_ingredients)

        return instance
