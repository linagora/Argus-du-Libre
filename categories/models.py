"""Models for multilingual categories."""

from django.db import models


class Category(models.Model):
    """Category model for organizing analysis fields."""

    weight = models.IntegerField(default=1, help_text="Weight for sorting categories")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["weight", "id"]

    def __str__(self):
        """Return the category name in English if available, otherwise the first translation."""
        translation = self.translations.filter(locale="en").first()
        if translation:
            return translation.name
        translation = self.translations.first()
        return translation.name if translation else f"Category {self.id}"

    def get_translation(self, locale):
        """Get translation for a specific locale."""
        return self.translations.filter(locale=locale).first()


class CategoryTranslation(models.Model):
    """Translation model for category names."""

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.CharField(
        max_length=10, help_text="Language code (e.g., 'en', 'fr', 'de')"
    )
    name = models.CharField(max_length=255, help_text="Category name in this language")

    class Meta:
        verbose_name = "Category Translation"
        verbose_name_plural = "Category Translations"
        unique_together = [["category", "locale"]]
        ordering = ["locale"]

    def __str__(self):
        """Return the translation in format: locale - name."""
        return f"{self.locale} - {self.name}"


class Field(models.Model):
    """Field model for analysis fields with periodicity settings."""

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="fields"
    )
    slug = models.SlugField(
        max_length=100, help_text="URL-friendly identifier for the field"
    )
    weight = models.IntegerField(default=1, help_text="Weight for sorting fields")
    analysis_periodicity_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Analysis periodicity in days (e.g., 7 for weekly, 30 for monthly, NULL for manual only)",
    )

    class Meta:
        verbose_name = "Field"
        verbose_name_plural = "Fields"
        ordering = ["category", "weight", "id"]
        unique_together = [["category", "slug"]]

    def __str__(self):
        """Return the field name in English if available, otherwise the first translation."""
        translation = self.translations.filter(locale="en").first()
        if translation:
            return translation.name
        translation = self.translations.first()
        return translation.name if translation else f"Field {self.id}"

    def get_translation(self, locale):
        """Get translation for a specific locale."""
        return self.translations.filter(locale=locale).first()


class FieldTranslation(models.Model):
    """Translation model for field names."""

    field = models.ForeignKey(
        Field, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.CharField(
        max_length=10, help_text="Language code (e.g., 'en', 'fr', 'de')"
    )
    name = models.CharField(max_length=255, help_text="Field name in this language")

    class Meta:
        verbose_name = "Field Translation"
        verbose_name_plural = "Field Translations"
        unique_together = [["field", "locale"]]
        ordering = ["locale"]

    def __str__(self):
        """Return the translation in format: locale - name."""
        return f"{self.locale} - {self.name}"


class Tag(models.Model):
    """Tag model for categorizing and linking similar softwares."""

    name = models.CharField(max_length=255, unique=True, help_text="Tag name")
    slug = models.SlugField(
        max_length=255, unique=True, help_text="URL-friendly identifier for the tag"
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    def __str__(self):
        """Return the tag name."""
        return self.name


class Software(models.Model):
    """Software/Project model being tracked."""

    STATE_DRAFT = "draft"
    STATE_IN_REVIEW = "in_review"
    STATE_PUBLISHED = "published"

    STATE_CHOICES = [
        (STATE_DRAFT, "Draft"),
        (STATE_IN_REVIEW, "In Review"),
        (STATE_PUBLISHED, "Published"),
    ]

    name = models.CharField(max_length=255, help_text="Software name")
    slug = models.SlugField(
        max_length=255, unique=True, help_text="URL-friendly identifier"
    )
    logo_url = models.TextField(blank=True, help_text="URL to the software logo")
    repository_url = models.TextField(
        blank=True, help_text="URL to the source code repository"
    )
    website_url = models.TextField(blank=True, help_text="URL to the software website")
    state = models.CharField(
        max_length=50,
        choices=STATE_CHOICES,
        default=STATE_DRAFT,
        help_text="Publication state",
    )
    tags = models.ManyToManyField(
        Tag, related_name="softwares", blank=True, help_text="Tags for categorization"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured_at = models.DateTimeField(
        null=True, blank=True, help_text="When the software was featured"
    )

    class Meta:
        verbose_name = "Software"
        verbose_name_plural = "Softwares"
        ordering = ["-created_at"]

    def __str__(self):
        """Return the software name."""
        return self.name
