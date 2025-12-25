from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import Subscription, User


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name")
    list_display_links = ("id", "username")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser")
    ordering = ("id",)
    empty_value_display = "—"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "author")
    list_display_links = ("id", "user")
    search_fields = ("user__email", "author__email")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "author")
