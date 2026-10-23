from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User, normalize_email


class EmailUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name")

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже есть.")
        return email


class EmailUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        taken = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("Пользователь с таким email уже есть.")
        return email


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = EmailUserChangeForm
    add_form = EmailUserCreationForm
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "full_name")
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("full_name",)}),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2"),
            },
        ),
    )
