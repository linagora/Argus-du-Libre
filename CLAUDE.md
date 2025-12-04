# CLAUDE.md

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
- Block (inline with Software, stores locale directly)

**Key conventions:**
- `__str__` methods prefer English ("en") translation, fall back to first available
- All translation models use `related_name="translations"`
- Locale codes are stored as strings (e.g., "en", "fr", "de")

### App Renaming Pattern (Database Compatibility)

The `projects` app was renamed from `categories` while preserving database table names:

```python
# projects/apps.py
class ProjectsConfig(AppConfig):
    name = "projects"           # Python package name
    label = "categories"        # Database table prefix
    verbose_name = "Projects"   # Admin display name
```

This keeps all database tables prefixed with `categories_*` while using `projects` in Python imports.

### OIDC Authentication Architecture

**Conditional authentication** based on `OIDC_ENABLED` environment variable:

1. **Custom Backend** (`argus_du_libre/auth.py`): Auto-grants admin privileges to OIDC users
2. **Custom Admin Site** (`argus_du_libre/admin.py`): Redirects `/admin` login to OIDC when enabled
3. **Settings Toggle** (`settings.py`): Switches between OIDC and ModelBackend

**Important:** Never use `admin.site.register()` - always use the custom `admin_site` from `argus_du_libre.admin`.

### Data Models

**Category → Field Hierarchy:**
- Categories organize Fields
- Fields have `slug` (unique per category), `weight`, and optional `analysis_periodicity_days`

**Software → Blocks:**
- Software has state workflow: draft → in_review → published
- Software has ManyToMany relationship with Tags
- Blocks store multilingual markdown content (overview, use_case, features)
- Each Software can have one Block per (kind, locale) combination

**Key constraints:**
- `UNIQUE(category_id, slug)` on Field
- `UNIQUE(software_id, kind, locale)` on Block
- `UNIQUE(slug)` on Tag and Software

**Analysis Results:**
- Links Software to Field with a score (1.00 to 5.00)
- Has `is_published` flag to control visibility
- Scores are used to calculate category and overall scores

## Public Pages Architecture

The project has a public-facing interface (`public` app) for browsing projects and their analysis results.

### Page Structure

**Homepage** (`/`)
- Shows up to 20 featured published projects
- Displays projects in card grid (1/2/4 columns responsive)
- Each card has logo, name, and "Read More" link
- Ordered by `featured_at` descending

**Project Detail** (`/project/<slug>/`)
- Header with logo, name, tags (clickable), overall score, website link
- Category cards with weighted scores and field details
- Overview block with markdown content
- Color-coded score badges (1=red to 5=green)
- All categories/fields use localized names from translation tables

**Tag Detail** (`/tag/<slug>/`)
- Shows all published projects with specific tag
- Same card layout as homepage
- Ordered by `featured_at`, then `created_at`

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

### Localization in Public Views

Public views retrieve localized content dynamically:

```python
locale = get_language()  # Current user locale

# Get localized names
category_translation = category.get_translation(locale)
category_name = category_translation.name if category_translation else str(category)
```

**Pattern:**
- Views use `get_translation(locale)` to fetch locale-specific strings
- Pass `*_name` strings to templates (not model objects)
- Templates use `{% trans %}` for UI strings
- Markdown content (Block model) is filtered by locale in query

### Markdown Rendering

Block content uses markdown with safe HTML rendering:

**Template filter** (`public/templatetags/markdown_extras.py`):
```python
@register.filter(name="markdown")
def markdown_format(text):
    return mark_safe(markdown.markdown(text, extensions=["fenced_code", "tables"]))
```

**Usage:**
```django
{% load markdown_extras %}
{{ overview_block.content|markdown }}
```

**Dependencies:**
- `markdown` library (installed via uv)

### Translation Workflow

**Adding new translatable strings:**

1. Mark strings in templates with `{% trans %}`:
```django
{% load i18n %}
<h1>{% trans "New Feature Title" %}</h1>
```

2. Generate translation files:
```bash
uv run python manage.py makemessages -l fr --no-location --no-obsolete
```

3. Edit `public/locale/fr/LC_MESSAGES/django.po`:
```
msgid "New Feature Title"
msgstr "Nouveau titre de fonctionnalité"
```

4. Compile translations:
```bash
uv run python manage.py compilemessages -l fr
```

**Supported languages:** English (en), French (fr)

## Configuration

All configuration uses environment variables loaded from `.env` file:

**Critical variables:**
- `OIDC_ENABLED=True/False` - Switches authentication backend
- `DB_*` - PostgreSQL connection settings
- `SECRET_KEY` - Django secret (required for production)
- `DEBUG=True/False` - Debug mode toggle

## Testing Patterns

When writing tests:

1. **Override OIDC settings** for admin tests:
```python
@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class MyAdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(...)
        self.client.login(username="admin", password="password")
```

2. **Test categories** (see `projects/tests.py`):
   - Model tests (creation, defaults, __str__, constraints, ordering)
   - Translation tests (unique constraints, fallback behavior)
   - Relationship tests (ForeignKey, ManyToMany, cascade deletes)
   - Admin tests (list, create, read, update, delete, filters, search)

3. **Test public views** (see `public/tests.py`):
   - View tests (status codes, templates, 404 handling)
   - Content tests (verify correct data is displayed)
   - Score calculation tests (verify weighted mean formulas)
   - Localization tests (test both English and French with explicit locale)
   - Edge case tests (empty states, missing data, unpublished content)

4. **Use `TestCase`** (not `SimpleTestCase`) - database access is required

5. **Test localization explicitly** when needed:
```python
# Test English page
response = self.client.get("/en/page/", HTTP_ACCEPT_LANGUAGE="en")
self.assertContains(response, "English Text")

# Test French page
response = self.client.get("/fr/page/", HTTP_ACCEPT_LANGUAGE="fr")
self.assertContains(response, "Texte français")
```

## Code Style

- **Line length:** 88 characters (Black-compatible)
- **Import ordering:** Enforced by isort via ruff
- **Django-specific rules:** Enabled (DJ ruleset)
- **Auto-formatting:** Handled by Claude Code hook
