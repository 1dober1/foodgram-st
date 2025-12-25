from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import RecipePageNumberPagination
from api.serializers import (
    AuthorSubscriptionSerializer,
    AvatarSerializer,
    CustomUserSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)
from api.utils import generate_shopping_cart_txt
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение: автор может редактировать, остальные только читают."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user


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

    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = RecipePageNumberPagination

    def get_queryset(self):
        """Оптимизирует запросы для рецептов с аннотациями."""
        queryset = (
            Recipe.objects.select_related("author")
            .prefetch_related(
                "tags",
                "ingredients",
            )
        )

        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user, recipe=OuterRef("pk")
                    )
                ),
            )
        return queryset

    def get_serializer_class(self):
        """Возвращает нужный сериализатор в зависимости от метода."""
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="get-link",
    )
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        if not pk.isdigit():
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe_url = request.build_absolute_uri(f"/api/recipes/{recipe.pk}/")
        return Response({"short-link": recipe_url}, status=status.HTTP_200_OK)

    def _add_to_list(self, model, user, pk):
        """Добавляет рецепт в список (избранное или корзина)."""
        if not pk.isdigit():
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        _, created = model.objects.get_or_create(user=user, recipe=recipe)
        if not created:
            return Response(
                {"detail": "Рецепт уже добавлен."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RecipeShortSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_from_list(self, model, user, pk):
        """Удаляет рецепт из списка (избранное или корзина)."""
        if not pk.isdigit():
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if not deleted:
            return Response(
                {"detail": "Рецепт не был добавлен ранее."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавить/удалить рецепт в избранное."""
        if request.method == "POST":
            return self._add_to_list(Favorite, request.user, pk)
        return self._remove_from_list(Favorite, request.user, pk)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        """Добавить/удалить рецепт в корзину покупок."""
        if request.method == "POST":
            return self._add_to_list(ShoppingCart, request.user, pk)
        return self._remove_from_list(ShoppingCart, request.user, pk)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в виде текстового файла."""
        return generate_shopping_cart_txt(request.user)


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями и подписками."""

    pagination_class = RecipePageNumberPagination

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        """Получить информацию о текущем пользователе."""
        serializer = CustomUserSerializer(
            request.user,
            context={"request": request},
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        """Создать или удалить подписку на пользователя."""
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == "POST":
            serializer = AuthorSubscriptionSerializer(
                author,
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            Subscription.objects.get_or_create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            deleted, _ = Subscription.objects.filter(
                user=user,
                author=author,
            ).delete()
            if not deleted:
                return Response(
                    {"detail": "Вы не подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
            .prefetch_related("recipes")
            .annotate(recipes_count=Count("recipes"))
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

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_avatar(self, request):
        """Загрузка или удаление аватара пользователя."""
        user = request.user

        if request.method == "PUT":
            serializer = AvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.avatar = serializer.validated_data["avatar"]
            user.save()
            avatar_url = user.avatar.url if user.avatar else None
            if avatar_url and not avatar_url.startswith("http"):
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
