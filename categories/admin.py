"""Admin configuration for categories."""

from django.contrib import admin

from argus_du_libre.admin import admin_site
from categories.models import Category, CategoryTranslation


class CategoryTranslationInline(admin.TabularInline):
    """Inline admin for category translations."""

    model = CategoryTranslation
    extra = 0
    min_num = 2
    max_num = 10
    fields = ["locale", "name"]


@admin.register(Category, site=admin_site)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for categories with multilingual support."""

    list_display = ["id", "get_name_en", "get_name_fr", "weight"]
    list_editable = ["weight"]
    ordering = ["weight", "id"]
    inlines = [CategoryTranslationInline]

    def get_name_en(self, obj):
        """Get English name."""
        translation = obj.get_translation("en")
        return translation.name if translation else "-"

    get_name_en.short_description = "Name (English)"

    def get_name_fr(self, obj):
        """Get French name."""
        translation = obj.get_translation("fr")
        return translation.name if translation else "-"

    get_name_fr.short_description = "Name (French)"
