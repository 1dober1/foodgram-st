from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from users.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=200)
    measurement_unit = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=200)
    color = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(
                r"^#[0-9a-fA-F]{6}$", "Цвет должен быть в формате HEX (#ffffff)"
            )
        ],
    )
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to="recipes/")
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    tags = models.ManyToManyField(Tag)
    ingredients = models.ManyToManyField(Ingredient, through="RecipeIngredient")
    pub_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"], name="unique_recipe_ingredient"
            )
        ]
