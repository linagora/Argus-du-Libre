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
    last_metrics_update_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When metrics were last updated for this software",
    )

    class Meta:
        verbose_name = "Software"
        verbose_name_plural = "Softwares"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["state", "last_metrics_update_at"],
                name="idx_soft_last_metrics_upd",
                condition=models.Q(state="published"),
            ),
        ]

    def __str__(self):
        """Return the software name."""
        return self.name


class Block(models.Model):
    """Content block model for multilingual software descriptions."""

    KIND_OVERVIEW = "overview"
    KIND_USE_CASE = "use_case"
    KIND_FEATURES = "features"

    KIND_CHOICES = [
        (KIND_OVERVIEW, "Overview"),
        (KIND_USE_CASE, "Use Case"),
        (KIND_FEATURES, "Features"),
    ]

    software = models.ForeignKey(
        Software, on_delete=models.CASCADE, related_name="blocks"
    )
    kind = models.CharField(
        max_length=50, choices=KIND_CHOICES, help_text="Type of content block"
    )
    locale = models.CharField(
        max_length=10, help_text="Language code (e.g., 'en', 'fr', 'de')"
    )
    content = models.TextField(help_text="Markdown content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Block"
        verbose_name_plural = "Blocks"
        unique_together = [["software", "kind", "locale"]]
        ordering = ["software", "kind", "locale"]

    def __str__(self):
        """Return block description."""
        return f"{self.software.name} - {self.get_kind_display()} ({self.locale})"


class AnalysisResult(models.Model):
    """Analysis results for each software and field combination."""

    software = models.ForeignKey(
        Software, on_delete=models.CASCADE, related_name="analysis_results"
    )
    field = models.ForeignKey(
        Field, on_delete=models.CASCADE, related_name="analysis_results"
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Analysis score (1.00 to 5.00)",
    )
    is_published = models.BooleanField(
        default=False, help_text="Whether the result is published"
    )
    is_manual = models.BooleanField(
        default=False, help_text="TRUE if manually entered/corrected"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Analysis Result"
        verbose_name_plural = "Analysis Results"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["software", "field"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        """Return analysis result description."""
        return f"{self.software.name} - {self.field} - {self.score}"

    def clean(self):
        """Validate that score is between 1 and 5."""
        from django.core.exceptions import ValidationError

        if self.score is not None and (self.score < 1 or self.score > 5):
            raise ValidationError({"score": "Score must be between 1.00 and 5.00"})


class Metric(models.Model):
    """Metric definition for automated data collection."""

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="metrics")
    slug = models.SlugField(
        max_length=100, help_text="URL-friendly identifier for the metric"
    )
    weight = models.IntegerField(
        default=1, help_text="Weight for aggregating multiple metrics"
    )
    collection_enabled = models.BooleanField(
        default=True, help_text="Whether automated collection is enabled"
    )

    class Meta:
        verbose_name = "Metric"
        verbose_name_plural = "Metrics"
        ordering = ["field", "weight", "id"]
        unique_together = [["field", "slug"]]
        indexes = [
            models.Index(fields=["field", "collection_enabled"]),
        ]

    def __str__(self):
        """Return the metric name in English if available, otherwise the first translation."""
        translation = self.translations.filter(locale="en").first()
        if translation:
            return translation.name
        translation = self.translations.first()
        return translation.name if translation else f"Metric {self.id}"

    def get_translation(self, locale):
        """Get translation for a specific locale."""
        return self.translations.filter(locale=locale).first()


class MetricTranslation(models.Model):
    """Translation model for metric names and descriptions."""

    metric = models.ForeignKey(
        Metric, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.CharField(
        max_length=10, help_text="Language code (e.g., 'en', 'fr', 'de')"
    )
    name = models.CharField(max_length=255, help_text="Metric name in this language")
    description = models.TextField(
        blank=True, help_text="Metric description in this language"
    )

    class Meta:
        verbose_name = "Metric Translation"
        verbose_name_plural = "Metric Translations"
        unique_together = [["metric", "locale"]]
        ordering = ["locale"]

    def __str__(self):
        """Return the translation in format: locale - name."""
        return f"{self.locale} - {self.name}"


class MetricValue(models.Model):
    """Historical metric values collected over time."""

    metric = models.ForeignKey(Metric, on_delete=models.CASCADE, related_name="values")
    software = models.ForeignKey(
        Software, on_delete=models.CASCADE, related_name="metric_values"
    )
    value = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text="Metric value (e.g., 45000 for GitHub stars, 0.85 for percentages)",
    )
    collected_at = models.DateTimeField(
        auto_now_add=True, help_text="When this value was collected"
    )
    source = models.CharField(
        max_length=255, blank=True, help_text="Source of the data (e.g., 'GitHub API')"
    )

    class Meta:
        verbose_name = "Metric Value"
        verbose_name_plural = "Metric Values"
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["metric", "software", "-collected_at"]),
            models.Index(fields=["software", "-collected_at"]),
        ]

    def __str__(self):
        """Return metric value description."""
        return f"{self.software.name} - {self.metric} - {self.value} ({self.collected_at.date()})"
