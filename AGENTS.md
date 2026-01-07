# Argus du Libre

## Project Overview

Argus du Libre is a Django 5.2.8 application for managing free and open-source software information with multilingual support.

**Tech Stack:**
- Python 3.13
- Django 5.2.8
- PostgreSQL (psycopg3)
- uv (package manager)
- ruff (linting and formatting)

## Architecture Overview

### Multilingual Data Pattern

The project uses a **translation table pattern** for multilingual content. This is the core architectural pattern used throughout:

1. **Main Entity**: Stores structural data, relationships, and non-translatable fields
2. **Translation Entity**: Stores locale-specific strings with UNIQUE(entity_id, locale) constraint
3. **Admin Integration**: Uses TabularInline or StackedInline for editing translations

**Example:**
```python
# Main entity
class Category(models.Model):
    weight = models.IntegerField(default=1)

# Translation entity
class CategoryTranslation(models.Model):
    category = models.ForeignKey(Category, related_name="translations")
    locale = models.CharField(max_length=10)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = [["category", "locale"]]
```

**Models using this pattern:**
- Category/CategoryTranslation
- Field/FieldTranslation
- Metric/MetricTranslation
- Block (inline with Software, stores locale directly)

**Key conventions:**
- `__str__` methods prefer English ("en") translation, fall back to first available
- All translation models use `related_name="translations"`
- Locale codes are stored as strings (e.g., "en", "fr", "de")

### App Renaming Pattern

The `projects` app uses `label = "categories"` in `apps.py` to preserve database table prefix `categories_*` while using `projects` in Python imports.

### OIDC Authentication

Conditional authentication via `OIDC_ENABLED` environment variable. Custom backend auto-grants admin privileges. Custom admin site redirects `/admin` login when enabled.

**Important:** Always use `admin_site` from `argus_du_libre.admin`, never `admin.site.register()`.

### Data Models

**Category → Field → Metric Hierarchy:**
- Categories organize Fields
- Fields have `slug` (unique per category), `weight`, and optional `analysis_periodicity_days`
- Metrics belong to Fields and define what data to collect (e.g., "GitHub Stars")
- Metrics have `slug` (unique per field), `weight`, and `collection_enabled`

**Software → Blocks:**
- Software has state workflow: draft → in_review → published
- Software has ManyToMany relationship with Tags
- Blocks store multilingual markdown content (overview, use_case, features)
- Each Software can have one Block per (kind, locale) combination

**Key constraints:**
- `UNIQUE(category_id, slug)` on Field
- `UNIQUE(field_id, slug)` on Metric
- `UNIQUE(software_id, kind, locale)` on Block
- `UNIQUE(slug)` on Tag and Software

**Analysis Results:**
- Links Software to Field with a score (1.00 to 5.00)
- Has `is_published` flag to control visibility
- Scores are used to calculate category and overall scores

**Metric Values:**
- Links Software to Metric with a raw decimal value
- Supports historical tracking (no unique constraint - multiple values over time)
- Stores `collected_at` timestamp and `source` (e.g., "GitHub API", "qsos-lng")
- All values stored as `NUMERIC(20, 4)` decimals (works for counts, percentages, ratings)

### Metric Persistence System

The metric system stores raw data collected from external sources (GitHub API, npm registry, etc.) separately from final scores in AnalysisResult.

**Database Tables:**
- `categories_metric` - Metric definitions (what to collect)
- `categories_metrictranslation` - Multilingual names and descriptions
- `categories_metricvalue` - Historical raw values

**Workflow:**
1. Create Metric definitions in admin (e.g., "GitHub Stars" for Popularity field)
2. Add translations for each supported locale
3. Automated tools (qsos-lng) insert MetricValue records with raw data
4. AnalysisResult stores final calculated scores (manually or via automation)

**Example:**
```python
# Metric: GitHub Stars
field = Field.objects.get(slug="popularity")
metric = Metric.objects.create(
    field=field,
    slug="github-stars",
    weight=3
)

# Value: Django has 45,000 stars
MetricValue.objects.create(
    metric=metric,
    software=Software.objects.get(slug="django"),
    value=45000,
    source="GitHub API"
)

# Score: Maps to 4.0 (40k-80k range)
AnalysisResult.objects.create(
    software=Software.objects.get(slug="django"),
    field=field,
    score=4.0,
    is_published=True
)
```

**Key Design:**
- Metrics are field-specific (each field can have multiple metrics)
- Values use simple decimal storage (not polymorphic)
- Historical tracking enabled (no UNIQUE constraint on MetricValue)
- Scores remain in AnalysisResult for display consistency
- Integration-friendly for qsos-lng via direct SQL INSERT

## Public Pages Architecture

The project has a public-facing interface (`public` app) for browsing projects and their analysis results.

### URL Structure

All public URLs support i18n with language prefix (e.g., `/en/`, `/fr/`):

| URL Pattern | View | Description |
|-------------|------|-------------|
| `/` | `home` | Homepage with featured projects |
| `/search/` | `search` | Full-text search results |
| `/compare/` | `compare` | Side-by-side project comparison |
| `/project/<slug>/` | `project_detail` | Individual project details |
| `/tag/<slug>/` | `tag_detail` | Projects filtered by tag |

### Page Structure

**Homepage** (`/`): Featured projects grid with search form, ordered by `featured_at`

**Project Detail** (`/project/<slug>/`): Shows scores by category/field, comparison selector, and overview block

**Tag Detail** (`/tag/<slug>/`): Filtered project list by tag

**Search** (`/search/?q=<query>`): Full-text search in names and locale-specific block content
- Query: `Q(name__icontains=query) | Q(blocks__content__icontains=query, blocks__locale=locale)`
- Returns distinct published projects ordered by `featured_at`

**Comparison** (`/compare/?projects=slug1,slug2,...`): Side-by-side table comparing 2-5 projects
- Validates all projects exist and are published
- Shows overall, category, and field scores
- Handles missing scores gracefully (shows "—")
- Accessed via multi-select dropdown on project detail pages

### Score Calculation System

The project uses a **weighted mean** system for scoring:

1. **Field Scores** (AnalysisResult):
   - Stored as Decimal (1.00 to 5.00)
   - Only published results are displayed

2. **Category Scores**:
   - Weighted mean of field scores using field weights
   - Formula: `Σ(field_score × field_weight) / Σ(field_weight)`
   - Calculated in view, passed to template

3. **Overall Score**:
   - Weighted mean of category scores using category weights
   - Formula: `Σ(category_score × category_weight) / Σ(category_weight)`
   - Displayed on project detail page

**Example:**
```python
# Field scores: Code Quality (4.5, weight=2), Performance (3.0, weight=1)
# Category score = (4.5 × 2 + 3.0 × 1) / (2 + 1) = 4.0
```

### Localization

**Pattern:** Views use `get_translation(locale)` to fetch locale-specific category/field names. Templates use `{% trans %}` for UI strings. Block content filtered by locale in queries.

**Translation Workflow:**
1. Mark strings: `{% trans "Text" %}`
2. Generate: `uv run python manage.py makemessages -l fr --no-location --no-obsolete`
3. Edit: `public/locale/fr/LC_MESSAGES/django.po`
4. Compile: `uv run python manage.py compilemessages -l fr`

**Supported languages:** English (en), French (fr)

**Markdown:** Block content rendered using custom `markdown` filter with `mark_safe()` and extensions `["fenced_code", "tables"]`

## Configuration

All configuration uses environment variables loaded from `.env` file:

**Critical variables:**
- `OIDC_ENABLED=True/False` - Switches authentication backend
- `DB_*` - PostgreSQL connection settings
- `SECRET_KEY` - Django secret (required for production)
- `DEBUG=True/False` - Debug mode toggle

## Testing Patterns

**Key Practices:**
- Override OIDC settings for admin tests: `@override_settings(OIDC_ENABLED=False, AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"])`
- Use `TestCase` (not `SimpleTestCase`) - database access required
- Test localization explicitly with `HTTP_ACCEPT_LANGUAGE` header

**Test Coverage** (see `projects/tests.py` and `public/tests.py`):
- Models: creation, constraints, relationships, translations
- Admin: CRUD operations, filters, search
- Public views: status codes, score calculations, localization, search/comparison functionality, edge cases

## Code Style

- **Line length:** 88 characters (Black-compatible)
- **Import ordering:** Enforced by isort via ruff
- **Django-specific rules:** Enabled (DJ ruleset)
- **Auto-formatting:** Handled by Claude Code hook
