from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "role", "status", "created_at")
    list_filter = ("status", "project__category")
    search_fields = ("user__email", "project__title", "role__name", "comment")
    autocomplete_fields = ("user", "project", "role")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user", "project", "role")
