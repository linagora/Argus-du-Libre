"""Admin configuration for projects."""

from django.contrib import admin

from argus_du_libre.admin import admin_site
from projects.models import (
    AnalysisResult,
    Block,
    Category,
    CategoryTranslation,
    Field,
    FieldTranslation,
    Software,
    Tag,
)


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


class FieldTranslationInline(admin.TabularInline):
    """Inline admin for field translations."""

    model = FieldTranslation
    extra = 0
    min_num = 2
    max_num = 10
    fields = ["locale", "name"]


@admin.register(Field, site=admin_site)
class FieldAdmin(admin.ModelAdmin):
    """Admin interface for fields with multilingual support."""

    list_display = [
        "id",
        "category",
        "get_name_en",
        "get_name_fr",
        "slug",
        "weight",
        "analysis_periodicity_days",
    ]
    list_editable = ["weight", "analysis_periodicity_days"]
    list_filter = ["category"]
    ordering = ["category", "weight", "id"]
    inlines = [FieldTranslationInline]
    fields = ["category", "slug", "weight", "analysis_periodicity_days"]

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


@admin.register(Tag, site=admin_site)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for tags."""

    list_display = ["id", "name", "slug"]
    search_fields = ["name", "slug"]
    ordering = ["name"]
    fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class BlockInline(admin.StackedInline):
    """Inline admin for content blocks."""

    model = Block
    extra = 0
    fields = ["kind", "locale", "content"]
    ordering = ["kind", "locale"]


@admin.register(Software, site=admin_site)
class SoftwareAdmin(admin.ModelAdmin):
    """Admin interface for software."""

    list_display = [
        "id",
        "name",
        "slug",
        "state",
        "get_tags",
        "created_at",
        "updated_at",
        "featured_at",
    ]
    list_filter = ["state", "tags", "created_at"]
    search_fields = ["name", "slug", "repository_url", "website_url"]
    ordering = ["-created_at"]
    filter_horizontal = ["tags"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BlockInline]
    fields = [
        "name",
        "slug",
        "logo_url",
        "repository_url",
        "website_url",
        "state",
        "tags",
        "featured_at",
    ]
    readonly_fields = ["created_at", "updated_at"]

    def get_tags(self, obj):
        """Get tags as comma-separated string."""
        return ", ".join([tag.name for tag in obj.tags.all()])

    get_tags.short_description = "Tags"


@admin.register(AnalysisResult, site=admin_site)
class AnalysisResultAdmin(admin.ModelAdmin):
    """Admin interface for analysis results."""

    list_display = [
        "id",
        "software",
        "field",
        "score",
        "is_published",
        "is_manual",
        "created_at",
    ]
    list_filter = ["is_published", "is_manual", "field", "software", "created_at"]
    list_editable = ["is_published", "is_manual"]
    search_fields = ["software__name", "field__translations__name"]
    ordering = ["-created_at"]
    fields = ["software", "field", "score", "is_published", "is_manual"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["software"]
