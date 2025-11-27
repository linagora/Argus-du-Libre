"""Tests for categories models and admin."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from categories.models import Category, CategoryTranslation

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
