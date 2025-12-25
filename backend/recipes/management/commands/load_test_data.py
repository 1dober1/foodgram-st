import base64

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import User


class Command(BaseCommand):
    help = "Создаёт тестовых пользователей, теги, ингредиенты и рецепты."

    SAMPLE_IMAGE = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMA"
        "AQAABQABDQottAAAAABJRU5ErkJggg=="
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Создание тестовых данных...")
        users = self._create_users()
        tags = self._create_tags()
        ingredients = self._create_ingredients()
        self._create_recipes(users, tags, ingredients)
        self.stdout.write(self.style.SUCCESS("Тестовые данные готовы."))

    def _create_users(self):
        users_data = [
            {
                "email": "demo1@example.com",
                "username": "demo1",
                "first_name": "Demo",
                "last_name": "User",
                "password": "demo12345",
            },
            {
                "email": "demo2@example.com",
                "username": "demo2",
                "first_name": "Chef",
                "last_name": "User",
                "password": "demo12345",
            },
        ]
        created_users = {}
        for data in users_data:
            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "username": data["username"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                },
            )
            if created:
                user.set_password(data["password"])
                user.save()
                self.stdout.write(f"  ✓ Пользователь {user.email} создан")
            else:
                self.stdout.write(
                    f"  • Пользователь {user.email} уже существует"
                )
            created_users[data["email"]] = user
        return created_users

    def _create_tags(self):
        tags_data = [
            {"name": "Завтрак", "color": "#E26C2D", "slug": "breakfast"},
            {"name": "Обед", "color": "#49B64E", "slug": "lunch"},
            {"name": "Ужин", "color": "#8775D2", "slug": "dinner"},
        ]
        tags = {}
        for tag in tags_data:
            obj, created = Tag.objects.get_or_create(
                slug=tag["slug"],
                defaults={"name": tag["name"], "color": tag["color"]},
            )
            message = "создан" if created else "уже существует"
            self.stdout.write(f"  • Тег {obj.slug} {message}")
            tags[tag["slug"]] = obj
        return tags

    def _create_ingredients(self):
        ingredients_data = [
            {"name": "Яйцо куриное", "measurement_unit": "шт"},
            {"name": "Молоко", "measurement_unit": "мл"},
            {"name": "Мука", "measurement_unit": "г"},
            {"name": "Соль", "measurement_unit": "г"},
            {"name": "Сахар", "measurement_unit": "г"},
            {"name": "Укроп", "measurement_unit": "г"},
            {"name": "Картофель", "measurement_unit": "г"},
            {"name": "Куриное филе", "measurement_unit": "г"},
        ]
        ingredients = {}
        for item in ingredients_data:
            obj, created = Ingredient.objects.get_or_create(
                name=item["name"],
                defaults={"measurement_unit": item["measurement_unit"]},
            )
            message = "создан" if created else "уже существует"
            self.stdout.write(f"  • Ингредиент {obj.name} {message}")
            ingredients[item["name"]] = obj
        return ingredients

    def _create_recipes(self, users, tags, ingredients):
        recipes_data = [
            {
                "name": "Омлет с зеленью",
                "author_email": "demo1@example.com",
                "text": "Быстрый завтрак из яиц с молоком и укропом.",
                "cooking_time": 10,
                "tags": ["breakfast"],
                "ingredients": [
                    {"name": "Яйцо куриное", "amount": 3},
                    {"name": "Молоко", "amount": 100},
                    {"name": "Укроп", "amount": 5},
                    {"name": "Соль", "amount": 2},
                ],
            },
            {
                "name": "Куриное филе с картофелем",
                "author_email": "demo2@example.com",
                "text": "Запечённое куриное филе с картофельным пюре.",
                "cooking_time": 40,
                "tags": ["dinner"],
                "ingredients": [
                    {"name": "Куриное филе", "amount": 300},
                    {"name": "Картофель", "amount": 400},
                    {"name": "Соль", "amount": 3},
                    {"name": "Молоко", "amount": 150},
                    {"name": "Сахар", "amount": 5},
                ],
            },
        ]

        for idx, recipe_data in enumerate(recipes_data, start=1):
            author = users.get(recipe_data["author_email"]) or next(
                iter(users.values())
            )
            recipe, created = Recipe.objects.get_or_create(
                name=recipe_data["name"],
                author=author,
                defaults={
                    "text": recipe_data["text"],
                    "cooking_time": recipe_data["cooking_time"],
                    "image": self._sample_image(f"sample_{idx}.png"),
                },
            )
            if not created:
                self.stdout.write(f"  • Рецепт «{recipe.name}» уже существует")
                continue

            # Теги
            recipe.tags.set(
                [tags[slug] for slug in recipe_data["tags"] if slug in tags]
            )

            # Ингредиенты
            recipe_ingredients = []
            for ingredient_data in recipe_data["ingredients"]:
                ingredient = ingredients.get(ingredient_data["name"])
                if ingredient is None:
                    ingredient, _ = Ingredient.objects.get_or_create(
                        name=ingredient_data["name"],
                        defaults={"measurement_unit": "шт"},
                    )
                    ingredients[ingredient.name] = ingredient
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=ingredient_data["amount"],
                    )
                )
            RecipeIngredient.objects.bulk_create(recipe_ingredients)
            self.stdout.write(f"  ✓ Рецепт «{recipe.name}» создан")

    def _sample_image(self, filename):
        """Возвращает минимальный PNG для обязательного поля image."""
        return ContentFile(base64.b64decode(self.SAMPLE_IMAGE), name=filename)
