#!/bin/bash

case "$OSTYPE" in
    msys*)    python=python ;;
    cygwin*)  python=python ;;
    *)        python=python3 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEARCH_ROOT="$SCRIPT_DIR/.."

# Ищем manage.py только внутри текущего проекта, чтобы не цеплять соседние репозитории
MANAGE_FILES=($(find "$SEARCH_ROOT" -maxdepth 3 -name "manage.py" -not -path "*/env/*" -not -path "*/venv/*"))

if [ ${#MANAGE_FILES[@]} -ne 1 ]; then
    echo "Убедитесь, что в проекте содержится ровно один файл manage.py"
    exit 1
fi

PATH_TO_MANAGE_PY="${MANAGE_FILES[0]}"
BASE_DIR="$(dirname "$PATH_TO_MANAGE_PY")"
cd "$BASE_DIR" || exit 1

# Полная очистка БД: рецепты, связанные модели, пользователи и сброс последовательностей
echo "from django.db import connection; \
from django.contrib.auth import get_user_model; \
from recipes.models import Recipe, RecipeIngredient, Favorite, ShoppingCart, Ingredient, Tag; \
from users.models import Subscription; \
User = get_user_model(); \
RecipeIngredient.objects.all().delete(); \
Favorite.objects.all().delete(); \
ShoppingCart.objects.all().delete(); \
Recipe.objects.all().delete(); \
Subscription.objects.all().delete(); \
Ingredient.objects.all().delete(); \
Tag.objects.all().delete(); \
User.objects.exclude(is_superuser=True).delete(); \
cursor = connection.cursor(); \
cursor.execute(\"DELETE FROM sqlite_sequence WHERE name IN ('recipes_ingredient', 'recipes_recipe', 'recipes_tag', 'users_user', 'recipes_favorite', 'recipes_shoppingcart', 'recipes_recipeingredient', 'users_subscription')\"); \
print('База данных полностью очищена и последовательности сброшены'); \
exit(0);" | $python manage.py shell
status=$?;
if [ $status -ne 0 ]; then
    echo "Ошибка при очистке БД.";
    exit $status;
fi

# Загрузка ингредиентов
$python manage.py load_ingredients --format json
status=$?;
if [ $status -ne 0 ]; then
    echo "Ошибка при загрузке ингредиентов.";
    exit $status;
fi

echo "База данных готова к тестированию."
