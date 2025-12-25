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
    AvatarSerializer,
    CustomUserSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение: автор может редактировать, остальные только читают."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author == request.user


class RecipePageNumberPagination(PageNumberPagination):
    """Пагинатор для рецептов."""

    page_size = 6
    page_size_query_param = "limit"
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

    def retrieve(self, request, *args, **kwargs):
        """Получение ингредиента по ID с проверкой существования."""
        instance = get_object_or_404(Ingredient, pk=kwargs.get("pk"))
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


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
        """Оптимизирует запросы для рецептов."""
        return (
            Recipe.objects.select_related("author")
            .prefetch_related(
                "tags",
                "ingredients",
                "favorite_set",
                "shoppingcart_set",
            )
            .order_by("-pub_date")
        )

    def get_serializer_class(self):
        """Возвращает нужный сериализатор в зависимости от метода."""
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора."""
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        read_serializer = RecipeReadSerializer(
            recipe,
            context={"request": request},
        )
        headers = self.get_success_headers(read_serializer.data)
        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        # Проверяем права доступа
        perm = IsAuthorOrReadOnly()
        if not perm.has_object_permission(request, self, instance):
            return Response(
                {"detail": "У вас нет прав для выполнения данного действия."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        read_serializer = RecipeReadSerializer(
            recipe,
            context={"request": request},
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта с проверкой прав доступа."""
        instance = self.get_object()
        # Проверяем права доступа
        perm = IsAuthorOrReadOnly()
        if not perm.has_object_permission(request, self, instance):
            return Response(
                {"detail": "У вас нет прав для выполнения данного действия."},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="get-link",
    )
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe_url = request.build_absolute_uri(f"/api/recipes/{recipe.pk}/")
        return Response({"short-link": recipe_url}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавить/удалить рецепт в избранное."""
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            fav, created = Favorite.objects.get_or_create(
                user=user,
                recipe=recipe,
            )
            if not created:
                return Response(
                    {"detail": "Рецепт уже в избранном"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            try:
                favorite = Favorite.objects.get(user=user, recipe=recipe)
            except Favorite.DoesNotExist:
                return Response(
                    {"detail": "Рецепт не найден в избранном"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        """Добавить/удалить рецепт в корзину покупок."""
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid recipe ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user=user,
                    recipe=recipe,
                )
            except ShoppingCart.DoesNotExist:
                return Response(
                    {"detail": "Рецепт не найден в корзине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в виде текстового файла."""
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shoppingcart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
            .order_by("ingredient__name")
        )

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

        txt_content = "\n".join(lines)

        response = HttpResponse(
            txt_content,
            content_type="text/plain; charset=utf-8",
        )
        response["Content-Disposition"] = (
            "attachment; filename=\"shopping_cart.txt\""
        )
        return response


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями и подписками.

    Наследуется от DjoserUserViewSet для поддержки стандартных операций
    (регистрация, активация, получение профиля), расширен методами подписок.
    """

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
            try:
                subscription = Subscription.objects.get(
                    user=user,
                    author=author,
                )
            except Subscription.DoesNotExist:
                return Response(
                    {"detail": "Вы не подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
            user.save()
            avatar_url = user.avatar.url if user.avatar else None
            if avatar_url and not avatar_url.startswith("http"):
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

        # DELETE
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
