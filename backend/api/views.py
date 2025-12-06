from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User

from api.filters import IngredientFilter, RecipeFilter
from api.serializers import (
    AuthorSubscriptionSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение: автор может редактировать, остальные только читают."""

    def has_object_permission(self, request, view, obj):
        # Разрешаем GET, HEAD, OPTIONS запросы всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешаем редактирование только автору
        return obj.author == request.user


class RecipePageNumberPagination(PageNumberPagination):
    """Пагинатор для рецептов."""

    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 100


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для тегов (только чтение)."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для ингредиентов (только чтение) с поиском по названию."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для рецептов с фильтрацией, пагинацией и управлением."""

    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = RecipePageNumberPagination

    def get_queryset(self):
        """Оптимизирует запросы для рецептов."""
        return Recipe.objects.select_related("author").prefetch_related(
            "tags", "ingredients", "favorite_set", "shoppingcart_set"
        )

    def get_serializer_class(self):
        """Использует RecipeReadSerializer для GET, RecipeWriteSerializer для других методов."""
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавить/удалить рецепт в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            favorite, created = Favorite.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response(
                    {"detail": "Рецепт уже в избранном"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            favorite = get_object_or_404(Favorite, user=user, recipe=recipe)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        """Добавить/удалить рецепт в корзину покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response(
                    {"detail": "Рецепт уже в корзине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            shopping_cart = get_object_or_404(ShoppingCart, user=user, recipe=recipe)
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в виде текстового файла."""
        # Получаем все ингредиенты из рецептов в корзине пользователя
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shoppingcart__user=request.user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        # Формируем текстовый контент
        lines = ["Список покупок:", "=" * 40]
        if not ingredients:
            lines.append("Корзина пуста!")
        else:
            for item in ingredients:
                name = item["ingredient__name"]
                amount = item["amount"]
                unit = item["ingredient__measurement_unit"]
                lines.append(f"• {name}: {amount} {unit}")

        txt_content = "\n".join(lines)

        # Возвращаем файл
        response = HttpResponse(txt_content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="shopping_cart.txt"'
        return response


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями и подписками.

    Наследуется от DjoserUserViewSet для поддержки стандартных операций
    (регистрация, активация, получение профиля), расширен методами подписок.
    """

    pagination_class = RecipePageNumberPagination

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        """Создать или удалить подписку на пользователя."""
        author = get_object_or_404(User, id=id)
        user = request.user

        if user == author:
            return Response(
                {"detail": "Вы не можете подписаться на самого себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            subscription, created = Subscription.objects.get_or_create(
                user=user, author=author
            )
            if not created:
                return Response(
                    {"detail": "Вы уже подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = AuthorSubscriptionSerializer(
                author, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            subscription = get_object_or_404(Subscription, user=user, author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        """Вернуть список авторов, на которых подписан пользователь."""
        subscriptions = (
            User.objects.filter(subscribing__user=request.user)
            .prefetch_related("recipe_set")
            .distinct()
        )
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = AuthorSubscriptionSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = AuthorSubscriptionSerializer(
            subscriptions, many=True, context={"request": request}
        )
        return Response(serializer.data)
