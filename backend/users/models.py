from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator()

    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(
        max_length=150, unique=True, validators=[username_validator]
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to="users/", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        ordering = ["id"]


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriber"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscribing"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique_user_author_subscription"
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")),
                name="user_cannot_subscribe_to_self",
            ),
        ]

    def clean(self):
        if self.user == self.author:
            raise ValidationError("Нельзя подписаться на самого себя.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
