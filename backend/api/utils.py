from django.db.models import Sum
from django.http import HttpResponse

from recipes.models import RecipeIngredient


def generate_shopping_cart_txt(user):
    """Генерирует текстовый файл со списком покупок."""
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

    response = HttpResponse(
        txt_content,
        content_type="text/plain; charset=utf-8",
    )
    response["Content-Disposition"] = (
        'attachment; filename="shopping_cart.txt"'
    )
    return response
