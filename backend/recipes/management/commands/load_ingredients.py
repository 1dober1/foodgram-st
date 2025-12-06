import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = (
        "Загружает ингредиенты из файла data/ingredients.json или data/ingredients.csv"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            type=str,
            default="json",
            choices=["json", "csv"],
            help="Формат файла (json или csv)",
        )

    def handle(self, *args, **options):
        file_format = options["format"]

        # Определяем путь к файлу
        base_path = Path(__file__).resolve().parent.parent.parent.parent.parent

        if file_format == "json":
            file_path = base_path / "data" / "ingredients.json"
            self.load_from_json(file_path)
        else:
            file_path = base_path / "data" / "ingredients.csv"
            self.load_from_csv(file_path)

    def load_from_json(self, file_path):
        """Загружает ингредиенты из JSON файла"""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"Файл не найден: {file_path}"))
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                ingredients_data = json.load(f)

            # Создаем объекты Ingredient
            ingredients = [
                Ingredient(
                    name=item["name"],
                    measurement_unit=item["measurement_unit"],
                )
                for item in ingredients_data
            ]

            # Используем bulk_create для быстрой загрузки
            Ingredient.objects.bulk_create(ingredients, batch_size=1000)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Успешно загружено {len(ingredients)} ингредиентов из JSON"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при загрузке JSON: {str(e)}"))

    def load_from_csv(self, file_path):
        """Загружает ингредиенты из CSV файла"""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"Файл не найден: {file_path}"))
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)

                # Создаем объекты Ingredient
                ingredients = [
                    Ingredient(
                        name=row[0],
                        measurement_unit=row[1],
                    )
                    for row in reader
                    if len(row) >= 2  # Проверяем, что строка содержит оба поля
                ]

            # Используем bulk_create для быстрой загрузки
            Ingredient.objects.bulk_create(ingredients, batch_size=1000)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Успешно загружено {len(ingredients)} ингредиентов из CSV"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при загрузке CSV: {str(e)}"))
