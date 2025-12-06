from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from recipes.models import Ingredient, Recipe, Tag

from api.filters import IngredientFilter, RecipeFilter
from api.serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
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
