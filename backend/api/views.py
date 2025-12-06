from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag

from api.filters import IngredientFilter, RecipeFilter
from api.serializers import (
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

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора."""
        serializer.save(author=self.request.user)
