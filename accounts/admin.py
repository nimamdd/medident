from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, PhoneOTP, ContactMessage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("id", "phone", "full_name", "is_active", "is_staff", "is_admin", "is_superuser")
    search_fields = ("phone", "full_name", "email")
    list_filter = ("is_active", "is_staff", "is_admin", "is_superuser", "date_joined")

    readonly_fields = ("id", "date_joined", "last_login", "password")

    fieldsets = (
        (None, {"fields": ("id", "phone", "password")}),
        ("Personal info", {"fields": ("full_name", "email", "national_id", "city", "address")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_admin", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "is_active", "is_staff", "is_admin", "is_superuser"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "code", "created_at", "expires_at", "used", "attempts_left")
    search_fields = ("phone",)
    list_filter = ("used", "created_at")
    readonly_fields = ("id", "created_at")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "created_at")
    search_fields = ("name", "phone")
    list_filter = ("created_at",)
    readonly_fields = ("id", "created_at")
