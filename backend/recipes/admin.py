from django.contrib import admin
from django.db.models import Count

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "color")
    list_display_links = ("id", "name")
    search_fields = ("name", "slug")


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    list_display_links = ("id", "name")
    search_fields = ("name",)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "author", "favorites_count", "pub_date")
    list_display_links = ("id", "name")
    list_filter = ("tags",)
    search_fields = (
        "name",
        "author__username",
        "author__email",
        "author__first_name",
        "author__last_name",
    )
    inlines = (RecipeIngredientInline,)
    readonly_fields = ("favorites_count",)
    ordering = ("-pub_date",)
    empty_value_display = "—"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset.select_related("author")
            .prefetch_related("tags", "ingredients")
            .annotate(fav_count=Count("favorite"))
        )

    def favorites_count(self, obj):
        return getattr(obj, "fav_count", 0)

    favorites_count.short_description = "В избранном"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    list_display_links = ("id", "recipe")
    search_fields = ("recipe__name", "ingredient__name")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("recipe", "ingredient")
        )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    list_display_links = ("id", "user")
    search_fields = ("user__email", "recipe__name")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "recipe")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    list_display_links = ("id", "user")
    search_fields = ("user__email", "recipe__name")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "recipe")
