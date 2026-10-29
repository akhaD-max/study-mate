from typing import ClassVar

from django.contrib import admin

from .models import Category, Project, ProjectMember, ProjectRole


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        "slug": ("name",),
    }


class ProjectRoleInline(admin.TabularInline):
    model = ProjectRole
    extra = 1
    fields = ("name", "description", "capacity", "occupied_display", "is_open")
    readonly_fields = ("occupied_display",)

    def get_queryset(self, request):
        return super().get_queryset(request).with_occupancy()

    @admin.display(description="Занято")
    def occupied_display(self, obj):
        if not obj or obj._state.adding:
            return 0
        return obj.occupied_places


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    fields = ("role", "user", "joined_at")
    readonly_fields = ("joined_at",)
    autocomplete_fields = ("user",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "role":
            object_id = (
                request.resolver_match.kwargs.get("object_id")
                if request.resolver_match
                else None
            )
            if object_id:
                kwargs["queryset"] = ProjectRole.objects.filter(project_id=object_id)
            else:
                kwargs["queryset"] = ProjectRole.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "author__email")
    autocomplete_fields = ("author", "category")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ProjectRoleInline, ProjectMemberInline)


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "capacity",
        "occupied_display",
        "free_display",
        "is_open",
        "created_at",
    )
    list_filter = ("is_open", "project__status", "project__category")
    search_fields = ("name", "description", "project__title")
    autocomplete_fields = ("project",)
    readonly_fields = ("occupied_display", "free_display", "created_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("project")
            .with_occupancy()
        )

    @admin.display(description="Занято")
    def occupied_display(self, obj):
        if not obj or obj._state.adding:
            return 0
        return obj.occupied_places

    @admin.display(description="Свободно")
    def free_display(self, obj):
        if not obj or obj._state.adding:
            return 0
        return obj.free_places


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "role", "joined_at")
    list_filter = ("project__category", "project__status")
    search_fields = ("project__title", "role__name", "user__email")
    autocomplete_fields = ("project", "role", "user")
    readonly_fields = ("joined_at",)
    list_select_related = ("project", "role", "user")
