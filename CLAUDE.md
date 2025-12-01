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

3. **Use `TestCase`** (not `SimpleTestCase`) - database access is required

## Code Style

- **Line length:** 88 characters (Black-compatible)
- **Import ordering:** Enforced by isort via ruff
- **Django-specific rules:** Enabled (DJ ruleset)
- **Auto-formatting:** Handled by Claude Code hook
