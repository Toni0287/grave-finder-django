from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class GraveFinderUserAdmin(UserAdmin):
    """Django's user admin with the extra ``role`` field."""

    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Grave Finder", {"fields": ("role",)}),)
