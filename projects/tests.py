"""Tests for projects models and admin."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from projects.models import (
    Block,
    Category,
    CategoryTranslation,
    Field,
    FieldTranslation,
    Software,
    Tag,
)

User = get_user_model()


class CategoryModelTestCase(TestCase):
    """Test cases for Category model."""

    def setUp(self):
        """Set up test fixtures."""
        self.category = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Security"
        )
        CategoryTranslation.objects.create(
            category=self.category, locale="fr", name="Sécurité"
        )

    def test_category_creation(self):
        """Test that a category can be created."""
        category = Category.objects.create(weight=2)
        self.assertIsNotNone(category.id)
        self.assertEqual(category.weight, 2)

    def test_category_default_weight(self):
        """Test that default weight is 1."""
        category = Category.objects.create()
        self.assertEqual(category.weight, 1)

    def test_category_str_returns_english_name(self):
        """Test that __str__ returns English name when available."""
        self.assertEqual(str(self.category), "Security")

    def test_category_str_returns_first_translation_if_no_english(self):
        """Test that __str__ returns first translation if no English."""
        category = Category.objects.create(weight=3)
        CategoryTranslation.objects.create(
            category=category, locale="fr", name="Français seulement"
        )
        # Should return French name since there's no English
        self.assertIn("Français", str(category))

    def test_category_str_returns_id_if_no_translations(self):
        """Test that __str__ returns ID if no translations exist."""
        category = Category.objects.create(weight=4)
        self.assertEqual(str(category), f"Category {category.id}")

    def test_get_translation(self):
        """Test getting translation by locale."""
        translation_en = self.category.get_translation("en")
        self.assertIsNotNone(translation_en)
        self.assertEqual(translation_en.name, "Security")

        translation_fr = self.category.get_translation("fr")
        self.assertIsNotNone(translation_fr)
        self.assertEqual(translation_fr.name, "Sécurité")

    def test_get_translation_returns_none_for_missing_locale(self):
        """Test that get_translation returns None for missing locale."""
        translation_de = self.category.get_translation("de")
        self.assertIsNone(translation_de)

    def test_category_ordering(self):
        """Test that categories are ordered by weight then id."""
        cat1 = Category.objects.create(weight=3)
        cat2 = Category.objects.create(weight=1)
        cat3 = Category.objects.create(weight=2)

        categories = list(Category.objects.all())
        # Should be ordered by weight
        self.assertEqual(categories[0].weight, 1)
        self.assertEqual(categories[1].weight, 1)  # self.category
        self.assertEqual(categories[2].weight, 2)
        self.assertEqual(categories[3].weight, 3)

    def test_category_cascade_delete(self):
        """Test that deleting a category deletes its translations."""
        category_id = self.category.id
        translation_count = CategoryTranslation.objects.filter(
            category_id=category_id
        ).count()
        self.assertEqual(translation_count, 2)

        self.category.delete()

        # Translations should be deleted
        translation_count = CategoryTranslation.objects.filter(
            category_id=category_id
        ).count()
        self.assertEqual(translation_count, 0)


class CategoryTranslationModelTestCase(TestCase):
    """Test cases for CategoryTranslation model."""

    def setUp(self):
        """Set up test fixtures."""
        self.category = Category.objects.create(weight=1)

    def test_translation_creation(self):
        """Test that a translation can be created."""
        translation = CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Test Category"
        )
        self.assertIsNotNone(translation.id)
        self.assertEqual(translation.locale, "en")
        self.assertEqual(translation.name, "Test Category")

    def test_translation_str(self):
        """Test translation string representation."""
        translation = CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Test"
        )
        self.assertEqual(str(translation), "en - Test")

    def test_unique_together_constraint(self):
        """Test that locale must be unique per category."""
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="First"
        )

        # Trying to create another English translation should fail
        with self.assertRaises(Exception):
            CategoryTranslation.objects.create(
                category=self.category, locale="en", name="Second"
            )

    def test_same_locale_different_categories(self):
        """Test that same locale can be used for different categories."""
        category2 = Category.objects.create(weight=2)

        translation1 = CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Category 1"
        )
        translation2 = CategoryTranslation.objects.create(
            category=category2, locale="en", name="Category 2"
        )

        self.assertIsNotNone(translation1.id)
        self.assertIsNotNone(translation2.id)
        self.assertNotEqual(translation1.id, translation2.id)


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class CategoryAdminTestCase(TestCase):
    """Test cases for Category admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.force_login(self.admin_user)

        self.category = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Security"
        )
        CategoryTranslation.objects.create(
            category=self.category, locale="fr", name="Sécurité"
        )

    def test_category_list_view_accessible(self):
        """Test that category list view is accessible."""
        response = self.client.get("/admin/categories/category/")
        self.assertEqual(response.status_code, 200)

    def test_category_list_displays_translations(self):
        """Test that category list displays English and French names."""
        response = self.client.get("/admin/categories/category/")
        self.assertContains(response, "Security")
        self.assertContains(response, "Sécurité")

    def test_category_add_view_accessible(self):
        """Test that category add view is accessible."""
        response = self.client.get("/admin/categories/category/add/")
        self.assertEqual(response.status_code, 200)

    def test_category_edit_view_accessible(self):
        """Test that category edit view is accessible."""
        response = self.client.get(
            f"/admin/categories/category/{self.category.id}/change/"
        )
        self.assertEqual(response.status_code, 200)

    def test_category_edit_view_shows_translations(self):
        """Test that edit view shows existing translations."""
        response = self.client.get(
            f"/admin/categories/category/{self.category.id}/change/"
        )
        self.assertContains(response, "Security")
        self.assertContains(response, "Sécurité")

    def test_create_category_with_translations(self):
        """Test creating a category through admin."""
        data = {
            "weight": 2,
            # Management form data for inline
            "translations-TOTAL_FORMS": "2",
            "translations-INITIAL_FORMS": "0",
            "translations-MIN_NUM_FORMS": "2",
            "translations-MAX_NUM_FORMS": "10",
            # Translation 1 (English)
            "translations-0-locale": "en",
            "translations-0-name": "Privacy",
            # Translation 2 (French)
            "translations-1-locale": "fr",
            "translations-1-name": "Confidentialité",
        }

        response = self.client.post(
            "/admin/categories/category/add/", data, follow=True
        )

        # Check that category was created
        self.assertEqual(Category.objects.count(), 2)
        new_category = Category.objects.get(weight=2)

        # Check translations
        en_translation = new_category.get_translation("en")
        self.assertIsNotNone(en_translation)
        self.assertEqual(en_translation.name, "Privacy")

        fr_translation = new_category.get_translation("fr")
        self.assertIsNotNone(fr_translation)
        self.assertEqual(fr_translation.name, "Confidentialité")

    def test_update_category(self):
        """Test updating a category through admin."""
        data = {
            "weight": 5,
            # Management form data for inline
            "translations-TOTAL_FORMS": "2",
            "translations-INITIAL_FORMS": "2",
            "translations-MIN_NUM_FORMS": "2",
            "translations-MAX_NUM_FORMS": "10",
            # Translation 1 (English) - existing
            "translations-0-id": self.category.translations.get(locale="en").id,
            "translations-0-category": self.category.id,
            "translations-0-locale": "en",
            "translations-0-name": "Security Updated",
            # Translation 2 (French) - existing
            "translations-1-id": self.category.translations.get(locale="fr").id,
            "translations-1-category": self.category.id,
            "translations-1-locale": "fr",
            "translations-1-name": "Sécurité Mise à jour",
        }

        response = self.client.post(
            f"/admin/categories/category/{self.category.id}/change/", data, follow=True
        )

        # Refresh from database
        self.category.refresh_from_db()

        # Check weight was updated
        self.assertEqual(self.category.weight, 5)

        # Check translations were updated
        en_translation = self.category.get_translation("en")
        self.assertEqual(en_translation.name, "Security Updated")

        fr_translation = self.category.get_translation("fr")
        self.assertEqual(fr_translation.name, "Sécurité Mise à jour")

    def test_delete_category(self):
        """Test deleting a category through admin."""
        category_id = self.category.id

        response = self.client.post(
            f"/admin/categories/category/{category_id}/delete/",
            {"post": "yes"},
            follow=True,
        )

        # Check that category was deleted
        self.assertFalse(Category.objects.filter(id=category_id).exists())
        # Translations should also be deleted due to CASCADE
        self.assertFalse(
            CategoryTranslation.objects.filter(category_id=category_id).exists()
        )


class FieldModelTestCase(TestCase):
    """Test cases for Field model."""

    def setUp(self):
        """Set up test fixtures."""
        self.category = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Security"
        )

        self.field = Field.objects.create(
            category=self.category,
            slug="license",
            weight=1,
            analysis_periodicity_days=30,
        )
        FieldTranslation.objects.create(
            field=self.field, locale="en", name="License"
        )
        FieldTranslation.objects.create(
            field=self.field, locale="fr", name="Licence"
        )

    def test_field_creation(self):
        """Test that a field can be created."""
        field = Field.objects.create(
            category=self.category, slug="privacy", weight=2
        )
        self.assertIsNotNone(field.id)
        self.assertEqual(field.weight, 2)
        self.assertEqual(field.slug, "privacy")

    def test_field_default_weight(self):
        """Test that default weight is 1."""
        field = Field.objects.create(category=self.category, slug="test")
        self.assertEqual(field.weight, 1)

    def test_field_periodicity_nullable(self):
        """Test that analysis_periodicity_days can be null."""
        field = Field.objects.create(
            category=self.category, slug="manual", analysis_periodicity_days=None
        )
        self.assertIsNone(field.analysis_periodicity_days)

    def test_field_str_returns_english_name(self):
        """Test that __str__ returns English name when available."""
        self.assertEqual(str(self.field), "License")

    def test_field_str_returns_first_translation_if_no_english(self):
        """Test that __str__ returns first translation if no English."""
        field = Field.objects.create(category=self.category, slug="french-only", weight=3)
        FieldTranslation.objects.create(
            field=field, locale="fr", name="Français seulement"
        )
        self.assertIn("Français", str(field))

    def test_field_str_returns_id_if_no_translations(self):
        """Test that __str__ returns ID if no translations exist."""
        field = Field.objects.create(category=self.category, slug="no-trans", weight=4)
        self.assertEqual(str(field), f"Field {field.id}")

    def test_get_translation(self):
        """Test getting translation by locale."""
        translation_en = self.field.get_translation("en")
        self.assertIsNotNone(translation_en)
        self.assertEqual(translation_en.name, "License")

        translation_fr = self.field.get_translation("fr")
        self.assertIsNotNone(translation_fr)
        self.assertEqual(translation_fr.name, "Licence")

    def test_get_translation_returns_none_for_missing_locale(self):
        """Test that get_translation returns None for missing locale."""
        translation_de = self.field.get_translation("de")
        self.assertIsNone(translation_de)

    def test_field_unique_slug_per_category(self):
        """Test that slug must be unique per category."""
        # Creating another field with same slug in same category should fail
        with self.assertRaises(Exception):
            Field.objects.create(category=self.category, slug="license", weight=2)

    def test_field_same_slug_different_categories(self):
        """Test that same slug can be used in different categories."""
        category2 = Category.objects.create(weight=2)
        field2 = Field.objects.create(category=category2, slug="license", weight=1)
        self.assertIsNotNone(field2.id)
        self.assertNotEqual(self.field.id, field2.id)

    def test_field_ordering(self):
        """Test that fields are ordered by category, weight, then id."""
        field1 = Field.objects.create(category=self.category, slug="field1", weight=3)
        field2 = Field.objects.create(category=self.category, slug="field2", weight=1)
        field3 = Field.objects.create(category=self.category, slug="field3", weight=2)

        fields = list(Field.objects.filter(category=self.category))
        self.assertEqual(fields[0].weight, 1)
        self.assertEqual(fields[1].weight, 1)  # self.field
        self.assertEqual(fields[2].weight, 2)
        self.assertEqual(fields[3].weight, 3)

    def test_field_cascade_delete(self):
        """Test that deleting a field deletes its translations."""
        field_id = self.field.id
        translation_count = FieldTranslation.objects.filter(field_id=field_id).count()
        self.assertEqual(translation_count, 2)

        self.field.delete()

        translation_count = FieldTranslation.objects.filter(field_id=field_id).count()
        self.assertEqual(translation_count, 0)

    def test_field_deleted_when_category_deleted(self):
        """Test that deleting a category deletes its fields."""
        field_id = self.field.id
        category_id = self.category.id

        self.category.delete()

        self.assertFalse(Field.objects.filter(id=field_id).exists())
        self.assertFalse(FieldTranslation.objects.filter(field_id=field_id).exists())


class FieldTranslationModelTestCase(TestCase):
    """Test cases for FieldTranslation model."""

    def setUp(self):
        """Set up test fixtures."""
        self.category = Category.objects.create(weight=1)
        self.field = Field.objects.create(category=self.category, slug="test", weight=1)

    def test_translation_creation(self):
        """Test that a translation can be created."""
        translation = FieldTranslation.objects.create(
            field=self.field, locale="en", name="Test Field"
        )
        self.assertIsNotNone(translation.id)
        self.assertEqual(translation.locale, "en")
        self.assertEqual(translation.name, "Test Field")

    def test_translation_str(self):
        """Test translation string representation."""
        translation = FieldTranslation.objects.create(
            field=self.field, locale="en", name="Test"
        )
        self.assertEqual(str(translation), "en - Test")

    def test_unique_together_constraint(self):
        """Test that locale must be unique per field."""
        FieldTranslation.objects.create(field=self.field, locale="en", name="First")

        with self.assertRaises(Exception):
            FieldTranslation.objects.create(field=self.field, locale="en", name="Second")

    def test_same_locale_different_fields(self):
        """Test that same locale can be used for different fields."""
        field2 = Field.objects.create(category=self.category, slug="test2", weight=2)

        translation1 = FieldTranslation.objects.create(
            field=self.field, locale="en", name="Field 1"
        )
        translation2 = FieldTranslation.objects.create(
            field=field2, locale="en", name="Field 2"
        )

        self.assertIsNotNone(translation1.id)
        self.assertIsNotNone(translation2.id)
        self.assertNotEqual(translation1.id, translation2.id)


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class FieldAdminTestCase(TestCase):
    """Test cases for Field admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.force_login(self.admin_user)

        self.category = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Security"
        )

        self.field = Field.objects.create(
            category=self.category,
            slug="license",
            weight=1,
            analysis_periodicity_days=30,
        )
        FieldTranslation.objects.create(field=self.field, locale="en", name="License")
        FieldTranslation.objects.create(field=self.field, locale="fr", name="Licence")

    def test_field_list_view_accessible(self):
        """Test that field list view is accessible."""
        response = self.client.get("/admin/categories/field/")
        self.assertEqual(response.status_code, 200)

    def test_field_list_displays_translations(self):
        """Test that field list displays English and French names."""
        response = self.client.get("/admin/categories/field/")
        self.assertContains(response, "License")
        self.assertContains(response, "Licence")

    def test_field_add_view_accessible(self):
        """Test that field add view is accessible."""
        response = self.client.get("/admin/categories/field/add/")
        self.assertEqual(response.status_code, 200)

    def test_field_edit_view_accessible(self):
        """Test that field edit view is accessible."""
        response = self.client.get(f"/admin/categories/field/{self.field.id}/change/")
        self.assertEqual(response.status_code, 200)

    def test_create_field_with_translations(self):
        """Test creating a field through admin."""
        data = {
            "category": self.category.id,
            "slug": "privacy-policy",
            "weight": 2,
            "analysis_periodicity_days": 7,
            "translations-TOTAL_FORMS": "2",
            "translations-INITIAL_FORMS": "0",
            "translations-MIN_NUM_FORMS": "2",
            "translations-MAX_NUM_FORMS": "10",
            "translations-0-locale": "en",
            "translations-0-name": "Privacy Policy",
            "translations-1-locale": "fr",
            "translations-1-name": "Politique de confidentialité",
        }

        response = self.client.post("/admin/categories/field/add/", data, follow=True)

        self.assertEqual(Field.objects.count(), 2)
        new_field = Field.objects.get(slug="privacy-policy")

        self.assertEqual(new_field.category, self.category)
        self.assertEqual(new_field.weight, 2)
        self.assertEqual(new_field.analysis_periodicity_days, 7)

        en_translation = new_field.get_translation("en")
        self.assertIsNotNone(en_translation)
        self.assertEqual(en_translation.name, "Privacy Policy")

        fr_translation = new_field.get_translation("fr")
        self.assertIsNotNone(fr_translation)
        self.assertEqual(fr_translation.name, "Politique de confidentialité")

    def test_update_field(self):
        """Test updating a field through admin."""
        data = {
            "category": self.category.id,
            "slug": "license",
            "weight": 5,
            "analysis_periodicity_days": 60,
            "translations-TOTAL_FORMS": "2",
            "translations-INITIAL_FORMS": "2",
            "translations-MIN_NUM_FORMS": "2",
            "translations-MAX_NUM_FORMS": "10",
            "translations-0-id": self.field.translations.get(locale="en").id,
            "translations-0-field": self.field.id,
            "translations-0-locale": "en",
            "translations-0-name": "License Updated",
            "translations-1-id": self.field.translations.get(locale="fr").id,
            "translations-1-field": self.field.id,
            "translations-1-locale": "fr",
            "translations-1-name": "Licence Mise à jour",
        }

        response = self.client.post(
            f"/admin/categories/field/{self.field.id}/change/", data, follow=True
        )

        self.field.refresh_from_db()

        self.assertEqual(self.field.weight, 5)
        self.assertEqual(self.field.analysis_periodicity_days, 60)

        en_translation = self.field.get_translation("en")
        self.assertEqual(en_translation.name, "License Updated")

        fr_translation = self.field.get_translation("fr")
        self.assertEqual(fr_translation.name, "Licence Mise à jour")

    def test_delete_field(self):
        """Test deleting a field through admin."""
        field_id = self.field.id

        response = self.client.post(
            f"/admin/categories/field/{field_id}/delete/",
            {"post": "yes"},
            follow=True,
        )

        self.assertFalse(Field.objects.filter(id=field_id).exists())
        self.assertFalse(FieldTranslation.objects.filter(field_id=field_id).exists())


class TagModelTestCase(TestCase):
    """Test cases for Tag model."""

    def test_tag_creation(self):
        """Test that a tag can be created."""
        tag = Tag.objects.create(name="Open Source", slug="open-source")
        self.assertIsNotNone(tag.id)
        self.assertEqual(tag.name, "Open Source")
        self.assertEqual(tag.slug, "open-source")

    def test_tag_str(self):
        """Test tag string representation."""
        tag = Tag.objects.create(name="Security", slug="security")
        self.assertEqual(str(tag), "Security")

    def test_tag_name_unique(self):
        """Test that tag name must be unique."""
        Tag.objects.create(name="Privacy", slug="privacy")
        with self.assertRaises(Exception):
            Tag.objects.create(name="Privacy", slug="privacy-2")

    def test_tag_slug_unique(self):
        """Test that tag slug must be unique."""
        Tag.objects.create(name="Privacy", slug="privacy")
        with self.assertRaises(Exception):
            Tag.objects.create(name="Privacy Policy", slug="privacy")

    def test_tag_ordering(self):
        """Test that tags are ordered by name."""
        tag1 = Tag.objects.create(name="Zebra", slug="zebra")
        tag2 = Tag.objects.create(name="Alpha", slug="alpha")
        tag3 = Tag.objects.create(name="Beta", slug="beta")

        tags = list(Tag.objects.all())
        self.assertEqual(tags[0].name, "Alpha")
        self.assertEqual(tags[1].name, "Beta")
        self.assertEqual(tags[2].name, "Zebra")


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class TagAdminTestCase(TestCase):
    """Test cases for Tag admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.force_login(self.admin_user)

        self.tag = Tag.objects.create(name="Open Source", slug="open-source")

    def test_tag_list_view_accessible(self):
        """Test that tag list view is accessible."""
        response = self.client.get("/admin/categories/tag/")
        self.assertEqual(response.status_code, 200)

    def test_tag_list_displays_tag(self):
        """Test that tag list displays tag name."""
        response = self.client.get("/admin/categories/tag/")
        self.assertContains(response, "Open Source")
        self.assertContains(response, "open-source")

    def test_tag_add_view_accessible(self):
        """Test that tag add view is accessible."""
        response = self.client.get("/admin/categories/tag/add/")
        self.assertEqual(response.status_code, 200)

    def test_tag_edit_view_accessible(self):
        """Test that tag edit view is accessible."""
        response = self.client.get(f"/admin/categories/tag/{self.tag.id}/change/")
        self.assertEqual(response.status_code, 200)

    def test_create_tag(self):
        """Test creating a tag through admin."""
        data = {
            "name": "Privacy",
            "slug": "privacy",
        }

        response = self.client.post("/admin/categories/tag/add/", data, follow=True)

        self.assertEqual(Tag.objects.count(), 2)
        new_tag = Tag.objects.get(slug="privacy")
        self.assertEqual(new_tag.name, "Privacy")

    def test_update_tag(self):
        """Test updating a tag through admin."""
        data = {
            "name": "Open Source Software",
            "slug": "open-source-software",
        }

        response = self.client.post(
            f"/admin/categories/tag/{self.tag.id}/change/", data, follow=True
        )

        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, "Open Source Software")
        self.assertEqual(self.tag.slug, "open-source-software")

    def test_delete_tag(self):
        """Test deleting a tag through admin."""
        tag_id = self.tag.id

        response = self.client.post(
            f"/admin/categories/tag/{tag_id}/delete/",
            {"post": "yes"},
            follow=True,
        )

        self.assertFalse(Tag.objects.filter(id=tag_id).exists())

    def test_search_by_name(self):
        """Test searching tags by name."""
        Tag.objects.create(name="Privacy", slug="privacy")
        Tag.objects.create(name="Security", slug="security")

        response = self.client.get("/admin/categories/tag/?q=Privacy")
        self.assertContains(response, "Privacy")
        self.assertNotContains(response, "Security")

    def test_search_by_slug(self):
        """Test searching tags by slug."""
        Tag.objects.create(name="Privacy", slug="privacy")
        Tag.objects.create(name="Security", slug="security")

        response = self.client.get("/admin/categories/tag/?q=security")
        self.assertContains(response, "Security")
        self.assertNotContains(response, "Privacy")


class SoftwareModelTestCase(TestCase):
    """Test cases for Software model."""

    def setUp(self):
        """Set up test fixtures."""
        self.tag1 = Tag.objects.create(name="Open Source", slug="open-source")
        self.tag2 = Tag.objects.create(name="Privacy", slug="privacy")

    def test_software_creation(self):
        """Test that a software can be created."""
        software = Software.objects.create(
            name="Firefox",
            slug="firefox",
            repository_url="https://github.com/mozilla/gecko-dev",
            website_url="https://www.mozilla.org/firefox/",
        )
        self.assertIsNotNone(software.id)
        self.assertEqual(software.name, "Firefox")
        self.assertEqual(software.slug, "firefox")
        self.assertEqual(software.state, Software.STATE_DRAFT)

    def test_software_default_state(self):
        """Test that default state is draft."""
        software = Software.objects.create(name="Test", slug="test")
        self.assertEqual(software.state, Software.STATE_DRAFT)

    def test_software_str(self):
        """Test software string representation."""
        software = Software.objects.create(name="Firefox", slug="firefox")
        self.assertEqual(str(software), "Firefox")

    def test_software_slug_unique(self):
        """Test that slug must be unique."""
        Software.objects.create(name="Firefox", slug="firefox")
        with self.assertRaises(Exception):
            Software.objects.create(name="Firefox Browser", slug="firefox")

    def test_software_state_choices(self):
        """Test that software can have different states."""
        software = Software.objects.create(
            name="Test", slug="test", state=Software.STATE_PUBLISHED
        )
        self.assertEqual(software.state, Software.STATE_PUBLISHED)

    def test_software_ordering(self):
        """Test that softwares are ordered by creation date (newest first)."""
        software1 = Software.objects.create(name="First", slug="first")
        software2 = Software.objects.create(name="Second", slug="second")
        software3 = Software.objects.create(name="Third", slug="third")

        softwares = list(Software.objects.all())
        self.assertEqual(softwares[0], software3)
        self.assertEqual(softwares[1], software2)
        self.assertEqual(softwares[2], software1)

    def test_software_tags_relationship(self):
        """Test many-to-many relationship with tags."""
        software = Software.objects.create(name="Firefox", slug="firefox")
        software.tags.add(self.tag1, self.tag2)

        self.assertEqual(software.tags.count(), 2)
        self.assertIn(self.tag1, software.tags.all())
        self.assertIn(self.tag2, software.tags.all())

    def test_software_tags_reverse_relationship(self):
        """Test reverse relationship from tags to softwares."""
        software1 = Software.objects.create(name="Firefox", slug="firefox")
        software2 = Software.objects.create(name="Tor Browser", slug="tor-browser")

        software1.tags.add(self.tag1)
        software2.tags.add(self.tag1)

        self.assertEqual(self.tag1.softwares.count(), 2)
        self.assertIn(software1, self.tag1.softwares.all())
        self.assertIn(software2, self.tag1.softwares.all())

    def test_software_timestamps(self):
        """Test that timestamps are set automatically."""
        software = Software.objects.create(name="Test", slug="test")
        self.assertIsNotNone(software.created_at)
        self.assertIsNotNone(software.updated_at)

    def test_software_featured_at_nullable(self):
        """Test that featured_at can be null."""
        software = Software.objects.create(name="Test", slug="test")
        self.assertIsNone(software.featured_at)


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class SoftwareAdminTestCase(TestCase):
    """Test cases for Software admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.force_login(self.admin_user)

        self.tag1 = Tag.objects.create(name="Open Source", slug="open-source")
        self.tag2 = Tag.objects.create(name="Privacy", slug="privacy")

        self.software = Software.objects.create(
            name="Firefox",
            slug="firefox",
            repository_url="https://github.com/mozilla/gecko-dev",
            website_url="https://www.mozilla.org/firefox/",
            state=Software.STATE_DRAFT,
        )
        self.software.tags.add(self.tag1)

    def test_software_list_view_accessible(self):
        """Test that software list view is accessible."""
        response = self.client.get("/admin/categories/software/")
        self.assertEqual(response.status_code, 200)

    def test_software_list_displays_software(self):
        """Test that software list displays software."""
        response = self.client.get("/admin/categories/software/")
        self.assertContains(response, "Firefox")
        self.assertContains(response, "firefox")

    def test_software_add_view_accessible(self):
        """Test that software add view is accessible."""
        response = self.client.get("/admin/categories/software/add/")
        self.assertEqual(response.status_code, 200)

    def test_software_edit_view_accessible(self):
        """Test that software edit view is accessible."""
        response = self.client.get(
            f"/admin/categories/software/{self.software.id}/change/"
        )
        self.assertEqual(response.status_code, 200)

    def test_create_software(self):
        """Test creating a software through admin."""
        data = {
            "name": "Thunderbird",
            "slug": "thunderbird",
            "repository_url": "https://github.com/mozilla/releases-comm-central",
            "website_url": "https://www.thunderbird.net/",
            "state": Software.STATE_DRAFT,
            "tags": [self.tag2.id],
            "logo_url": "",
            "featured_at": "",
            # Block inline data (no blocks)
            "blocks-TOTAL_FORMS": "0",
            "blocks-INITIAL_FORMS": "0",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
        }

        response = self.client.post(
            "/admin/categories/software/add/", data, follow=True
        )

        self.assertEqual(Software.objects.count(), 2)
        new_software = Software.objects.get(slug="thunderbird")
        self.assertEqual(new_software.name, "Thunderbird")
        self.assertEqual(new_software.state, Software.STATE_DRAFT)
        self.assertIn(self.tag2, new_software.tags.all())

    def test_update_software(self):
        """Test updating a software through admin."""
        data = {
            "name": "Firefox Browser",
            "slug": "firefox",
            "repository_url": "https://github.com/mozilla/gecko-dev",
            "website_url": "https://www.mozilla.org/firefox/new/",
            "state": Software.STATE_PUBLISHED,
            "tags": [self.tag1.id, self.tag2.id],
            "logo_url": "https://example.com/logo.png",
            "featured_at": "",
            # Block inline data (no blocks)
            "blocks-TOTAL_FORMS": "0",
            "blocks-INITIAL_FORMS": "0",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
        }

        response = self.client.post(
            f"/admin/categories/software/{self.software.id}/change/", data, follow=True
        )

        self.software.refresh_from_db()
        self.assertEqual(self.software.name, "Firefox Browser")
        self.assertEqual(self.software.state, Software.STATE_PUBLISHED)
        self.assertEqual(self.software.tags.count(), 2)
        self.assertIn(self.tag1, self.software.tags.all())
        self.assertIn(self.tag2, self.software.tags.all())

    def test_delete_software(self):
        """Test deleting a software through admin."""
        software_id = self.software.id

        response = self.client.post(
            f"/admin/categories/software/{software_id}/delete/",
            {"post": "yes"},
            follow=True,
        )

        self.assertFalse(Software.objects.filter(id=software_id).exists())

    def test_filter_by_state(self):
        """Test filtering softwares by state."""
        Software.objects.create(
            name="Published App",
            slug="published-app",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            f"/admin/categories/software/?state={Software.STATE_PUBLISHED}"
        )
        self.assertContains(response, "Published App")
        self.assertNotContains(response, "Firefox")

    def test_filter_by_tag(self):
        """Test filtering softwares by tag."""
        software2 = Software.objects.create(name="Tor Browser", slug="tor-browser")
        software2.tags.add(self.tag2)

        response = self.client.get(
            f"/admin/categories/software/?tags__id__exact={self.tag2.id}"
        )
        self.assertContains(response, "Tor Browser")
        self.assertNotContains(response, "Firefox")

    def test_search_by_name(self):
        """Test searching softwares by name."""
        Software.objects.create(name="Thunderbird", slug="thunderbird")

        response = self.client.get("/admin/categories/software/?q=Thunderbird")
        self.assertContains(response, "Thunderbird")


class BlockModelTestCase(TestCase):
    """Test cases for Block model."""

    def setUp(self):
        """Set up test fixtures."""
        self.software = Software.objects.create(name="Firefox", slug="firefox")
        self.block_en = Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="Firefox is a free and open-source web browser.",
        )
        self.block_fr = Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="fr",
            content="Firefox est un navigateur web libre et open-source.",
        )

    def test_block_creation(self):
        """Test that a block can be created."""
        block = Block.objects.create(
            software=self.software,
            kind=Block.KIND_FEATURES,
            locale="en",
            content="# Features\n\n- Fast\n- Secure\n- Private",
        )
        self.assertIsNotNone(block.id)
        self.assertEqual(block.kind, Block.KIND_FEATURES)
        self.assertEqual(block.locale, "en")
        self.assertIn("Fast", block.content)

    def test_block_kind_choices(self):
        """Test that block kind choices are correct."""
        self.assertEqual(Block.KIND_OVERVIEW, "overview")
        self.assertEqual(Block.KIND_USE_CASE, "use_case")
        self.assertEqual(Block.KIND_FEATURES, "features")

    def test_block_str_representation(self):
        """Test that __str__ returns meaningful description."""
        expected = f"{self.software.name} - Overview (en)"
        self.assertEqual(str(self.block_en), expected)

    def test_block_unique_together_constraint(self):
        """Test that unique constraint on (software, kind, locale) is enforced."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Block.objects.create(
                software=self.software,
                kind=Block.KIND_OVERVIEW,
                locale="en",
                content="Duplicate content",
            )

    def test_block_allows_same_kind_different_locale(self):
        """Test that same kind with different locale is allowed."""
        block = Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="de",
            content="Firefox ist ein freier Webbrowser.",
        )
        self.assertIsNotNone(block.id)
        self.assertEqual(Block.objects.filter(kind=Block.KIND_OVERVIEW).count(), 3)

    def test_block_allows_different_kind_same_locale(self):
        """Test that different kind with same locale is allowed."""
        block = Block.objects.create(
            software=self.software,
            kind=Block.KIND_FEATURES,
            locale="en",
            content="# Features",
        )
        self.assertIsNotNone(block.id)
        self.assertEqual(Block.objects.filter(locale="en").count(), 2)

    def test_block_cascade_delete_with_software(self):
        """Test that blocks are deleted when software is deleted."""
        software_id = self.software.id
        block_ids = [self.block_en.id, self.block_fr.id]

        self.software.delete()

        self.assertFalse(Software.objects.filter(id=software_id).exists())
        self.assertFalse(Block.objects.filter(id__in=block_ids).exists())

    def test_block_ordering(self):
        """Test that blocks are ordered by software, kind, locale."""
        software2 = Software.objects.create(name="Thunderbird", slug="thunderbird")
        Block.objects.create(
            software=software2,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="Email client",
        )
        Block.objects.create(
            software=self.software,
            kind=Block.KIND_FEATURES,
            locale="en",
            content="Features",
        )
        Block.objects.create(
            software=self.software,
            kind=Block.KIND_USE_CASE,
            locale="en",
            content="Use cases",
        )

        blocks = list(Block.objects.all())
        # Should be ordered by software ID, then kind, then locale
        # Get Firefox blocks (should be consecutive and ordered by kind)
        firefox_blocks = [b for b in blocks if b.software == self.software]
        self.assertEqual(len(firefox_blocks), 4)  # 2 from setUp + 2 from test
        # Within Firefox blocks, features comes first, then overview, then use_case
        self.assertEqual(firefox_blocks[0].kind, Block.KIND_FEATURES)
        self.assertEqual(firefox_blocks[1].kind, Block.KIND_OVERVIEW)
        self.assertEqual(firefox_blocks[2].kind, Block.KIND_OVERVIEW)
        self.assertEqual(firefox_blocks[3].kind, Block.KIND_USE_CASE)

    def test_block_timestamps(self):
        """Test that created_at and updated_at are set automatically."""
        self.assertIsNotNone(self.block_en.created_at)
        self.assertIsNotNone(self.block_en.updated_at)

    def test_block_markdown_content(self):
        """Test that markdown content is stored correctly."""
        markdown_content = """# Overview

Firefox is a **fast** and *secure* browser.

## Features
- Privacy protection
- Fast browsing
- Cross-platform
"""
        block = Block.objects.create(
            software=self.software,
            kind=Block.KIND_FEATURES,
            locale="en",
            content=markdown_content,
        )
        self.assertEqual(block.content, markdown_content)
        self.assertIn("**fast**", block.content)
        self.assertIn("## Features", block.content)


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class BlockAdminTestCase(TestCase):
    """Test cases for Block admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.login(username="admin", password="password")

        self.software = Software.objects.create(name="Firefox", slug="firefox")
        self.block = Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="Firefox is a web browser.",
        )

    def test_block_inline_in_software_admin(self):
        """Test that blocks appear as inline in software admin."""
        response = self.client.get(
            f"/admin/categories/software/{self.software.id}/change/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blocks")
        self.assertContains(response, self.block.content)

    def test_create_block_through_software_admin(self):
        """Test creating a block through software admin inline."""
        tag = Tag.objects.create(name="Browser", slug="browser")

        data = {
            "name": "Firefox",
            "slug": "firefox",
            "state": Software.STATE_DRAFT,
            "tags": [tag.id],
            "logo_url": "",
            "repository_url": "",
            "website_url": "",
            "featured_at": "",
            # Block inline data
            "blocks-TOTAL_FORMS": "2",
            "blocks-INITIAL_FORMS": "1",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-id": self.block.id,
            "blocks-0-kind": Block.KIND_OVERVIEW,
            "blocks-0-locale": "en",
            "blocks-0-content": "Updated overview",
            "blocks-1-kind": Block.KIND_FEATURES,
            "blocks-1-locale": "en",
            "blocks-1-content": "# Features\n- Fast\n- Secure",
        }

        response = self.client.post(
            f"/admin/categories/software/{self.software.id}/change/", data, follow=True
        )

        # Should have 2 blocks now
        self.assertEqual(self.software.blocks.count(), 2)
        features_block = Block.objects.get(
            software=self.software, kind=Block.KIND_FEATURES
        )
        self.assertEqual(features_block.locale, "en")
        self.assertIn("Fast", features_block.content)

    def test_update_block_through_software_admin(self):
        """Test updating a block through software admin inline."""
        tag = Tag.objects.create(name="Browser", slug="browser")

        data = {
            "name": "Firefox",
            "slug": "firefox",
            "state": Software.STATE_DRAFT,
            "tags": [tag.id],
            "logo_url": "",
            "repository_url": "",
            "website_url": "",
            "featured_at": "",
            # Block inline data
            "blocks-TOTAL_FORMS": "1",
            "blocks-INITIAL_FORMS": "1",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-id": self.block.id,
            "blocks-0-kind": Block.KIND_OVERVIEW,
            "blocks-0-locale": "fr",
            "blocks-0-content": "Firefox est un navigateur web.",
        }

        response = self.client.post(
            f"/admin/categories/software/{self.software.id}/change/", data, follow=True
        )

        self.block.refresh_from_db()
        self.assertEqual(self.block.locale, "fr")
        self.assertIn("navigateur", self.block.content)

    def test_delete_block_through_software_admin(self):
        """Test deleting a block through software admin inline."""
        tag = Tag.objects.create(name="Browser", slug="browser")
        block_id = self.block.id

        data = {
            "name": "Firefox",
            "slug": "firefox",
            "state": Software.STATE_DRAFT,
            "tags": [tag.id],
            "logo_url": "",
            "repository_url": "",
            "website_url": "",
            "featured_at": "",
            # Block inline data with DELETE
            "blocks-TOTAL_FORMS": "1",
            "blocks-INITIAL_FORMS": "1",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-id": self.block.id,
            "blocks-0-kind": Block.KIND_OVERVIEW,
            "blocks-0-locale": "en",
            "blocks-0-content": "Firefox is a web browser.",
            "blocks-0-DELETE": "on",
        }

        response = self.client.post(
            f"/admin/categories/software/{self.software.id}/change/", data, follow=True
        )

        self.assertFalse(Block.objects.filter(id=block_id).exists())
        self.assertEqual(self.software.blocks.count(), 0)
