from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов."""

    tags = filters.CharFilter(
        field_name="tags__slug", lookup_expr="in", method="filter_tags"
    )
    author = filters.NumberFilter(field_name="author__id")
    is_favorited = filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ("tags", "author", "is_favorited", "is_in_shopping_cart")

    def filter_tags(self, queryset, name, value):
        """Фильтрует рецепты по слагам тегов."""
        if not value:
            return queryset

        tags_list = value.split(",")
        return queryset.filter(tags__slug__in=tags_list).distinct()

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрует рецепты, добавленные в избранное текущим пользователем."""
        user = self.request.user

        if not user.is_authenticated or not value:
            return queryset

        return queryset.filter(favorite__user=user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрует рецепты, добавленные в корзину текущим пользователем."""
        user = self.request.user

        if not user.is_authenticated or not value:
            return queryset

        return queryset.filter(shoppingcart__user=user)


class IngredientFilter(filters.FilterSet):
    """Фильтр для ингредиентов."""

    name = filters.CharFilter(field_name="name", lookup_expr="istartswith")

    class Meta:
        model = Ingredient
        fields = ("name",)
