from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов."""

    tags = filters.AllValuesMultipleFilter(field_name="tags__slug")
    author = filters.NumberFilter(field_name="author__id")
    is_favorited = filters.NumberFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.NumberFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ("tags", "author", "is_favorited", "is_in_shopping_cart")

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрует рецепты, добавленные в избранное текущим пользователем."""
        request = self.request
        if not request:
            return queryset

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return queryset

        if value == 1:
            return queryset.filter(favorite__user=user).distinct()
        elif value == 0:
            return queryset.exclude(favorite__user=user).distinct()
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрует рецепты, добавленные в корзину текущим пользователем."""
        request = self.request
        if not request:
            return queryset

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return queryset

        if value == 1:
            return queryset.filter(shoppingcart__user=user).distinct()
        elif value == 0:
            return queryset.exclude(shoppingcart__user=user).distinct()
        return queryset


class IngredientFilter(filters.FilterSet):
    """Фильтр для ингредиентов."""

    name = filters.CharFilter(field_name="name", lookup_expr="istartswith")

    class Meta:
        model = Ingredient
        fields = ("name",)
