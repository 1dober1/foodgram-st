from django.contrib import admin

from users.models import Subscription, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "first_name", "last_name")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser")
    ordering = ("id",)
    empty_value_display = "—"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "author")
    search_fields = ("user__email", "author__email")
