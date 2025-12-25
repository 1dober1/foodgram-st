from rest_framework.pagination import PageNumberPagination


class RecipePageNumberPagination(PageNumberPagination):
    """Пагинатор для рецептов."""

    page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100
