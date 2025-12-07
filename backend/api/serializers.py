from base64 import b64decode

from django.core.files.base import ContentFile
from djoser.serializers import (
    UserSerializer,
    UserCreateSerializer as DjoserUserCreateSerializer,
)
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


class UserCreateSerializer(DjoserUserCreateSerializer):
    """Сериализатор для создания пользователя с обязательными полями."""

    class Meta(DjoserUserCreateSerializer.Meta):
        fields = ("email", "username", "first_name", "last_name", "password")

    def to_representation(self, instance):
        """Ограничиваем ответ после регистрации требуемыми полями."""
        return {
            "id": instance.id,
            "username": instance.username,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
        }


class RecipeShortForAuthorSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта для отображения в профиле автора."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class CustomUserSerializer(UserSerializer):
    """Расширенный сериализатор пользователя с информацией о подписке."""

    is_subscribed = serializers.SerializerMethodField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(read_only=True, allow_null=True)

    class Meta(UserSerializer.Meta):
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        )

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


class AuthorSubscriptionSerializer(CustomUserSerializer):
    """Сериализатор автора для отображения в списке подписок с его рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + ("recipes_count", "recipes")

    def get_recipes(self, obj):
        """Возвращает рецепты автора, ограниченные параметром recipes_limit."""
        request = self.context.get("request")
        recipes_limit = None

        if request:
            recipes_limit = request.query_params.get("recipes_limit")

        recipes = Recipe.objects.filter(author=obj)

        if recipes_limit:
            try:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            except (ValueError, TypeError):
                pass

        return RecipeShortForAuthorSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов автора."""
        return Recipe.objects.filter(author=obj).count()


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

    author = CustomUserSerializer()
    ingredients = RecipeIngredientSerializer(source="recipeingredient_set", many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
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


class AvatarSerializer(serializers.Serializer):
    """Сериализатор для загрузки аватара пользователя."""

    avatar = Base64ImageField()


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Сериализатор для ингредиентов при записи рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("ingredients", "tags", "image", "name", "text", "cooking_time")

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужно указать хотя бы один ингредиент.")
        ids = [item["id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться.")
        for item in value:
            if not Ingredient.objects.filter(id=item["id"]).exists():
                raise serializers.ValidationError("Указан несуществующий ингредиент.")
        return value

    def validate_tags(self, value):
        # Tags are optional, so empty list is valid
        if value and len(value) != len(set(value)):
            raise serializers.ValidationError("Теги не должны повторяться.")
        return value

    def validate(self, attrs):
        if attrs.get("cooking_time") is not None and attrs["cooking_time"] < 1:
            raise serializers.ValidationError(
                {"cooking_time": "Значение должно быть >= 1"}
            )

        # For updates (PATCH), ingredients are still required per API spec
        if self.instance is not None and "ingredients" not in attrs:
            raise serializers.ValidationError({"ingredients": "Это поле обязательно."})

        return attrs

    def create(self, validated_data):
        """Создает новый рецепт с ингредиентами и тегами."""
        # Извлекаем ingredients и tags из validated_data
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags", [])

        # Создаем рецепт с текущим пользователем как автор
        validated_data["author"] = self.context["request"].user
        recipe = Recipe.objects.create(**validated_data)

        # Устанавливаем теги (если есть)
        if tags_data:
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
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags", None)

        # Обновляем основные поля рецепта
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Если переданы теги, обновляем их
        if tags_data is not None:
            instance.tags.set(tags_data)

        # Обновляем ингредиенты
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
