"""Tests for OIDC authentication backend."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from argus_du_libre.auth import OIDCAdminAuthenticationBackend

User = get_user_model()


class OIDCAdminAuthenticationBackendTestCase(TestCase):
    """Test cases for OIDCAdminAuthenticationBackend."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = OIDCAdminAuthenticationBackend()
        self.test_claims = {
            "email": "test@example.com",
            "preferred_username": "testuser",
            "sub": "123456789",
        }

    def tearDown(self):
        """Clean up after tests."""
        User.objects.all().delete()

    def test_create_user_with_admin_privileges(self):
        """Test that create_user creates a user with admin privileges."""
        user = self.backend.create_user(self.test_claims)

        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_user_with_email_as_username(self):
        """Test that create_user uses email as username when preferred_username is missing."""
        claims = {"email": "test@example.com", "sub": "123456789"}
        user = self.backend.create_user(claims)

        self.assertIsNotNone(user)
        self.assertEqual(user.username, "test@example.com")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_update_user_updates_email(self):
        """Test that update_user updates the user's email."""
        user = User.objects.create_user(
            username="testuser",
            email="old@example.com",
        )

        updated_user = self.backend.update_user(user, self.test_claims)

        self.assertEqual(updated_user.email, "test@example.com")

    def test_update_user_ensures_admin_privileges(self):
        """Test that update_user ensures admin privileges are maintained."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            is_staff=False,
            is_superuser=False,
        )

        updated_user = self.backend.update_user(user, self.test_claims)

        self.assertTrue(updated_user.is_staff)
        self.assertTrue(updated_user.is_superuser)

    def test_update_user_preserves_admin_privileges(self):
        """Test that update_user preserves existing admin privileges."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            is_staff=True,
            is_superuser=True,
        )

        updated_user = self.backend.update_user(user, self.test_claims)

        self.assertTrue(updated_user.is_staff)
        self.assertTrue(updated_user.is_superuser)

    def test_filter_users_by_claims_finds_user_by_email(self):
        """Test that filter_users_by_claims finds user by email."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )

        users = self.backend.filter_users_by_claims(self.test_claims)

        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), user)

    def test_filter_users_by_claims_case_insensitive(self):
        """Test that filter_users_by_claims is case-insensitive."""
        user = User.objects.create_user(
            username="testuser",
            email="TEST@EXAMPLE.COM",
        )

        claims = {
            "email": "test@example.com",
            "preferred_username": "testuser",
        }
        users = self.backend.filter_users_by_claims(claims)

        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), user)

    def test_filter_users_by_claims_returns_empty_without_email(self):
        """Test that filter_users_by_claims returns empty queryset without email."""
        claims = {"preferred_username": "testuser", "sub": "123456789"}
        users = self.backend.filter_users_by_claims(claims)

        self.assertEqual(users.count(), 0)

    def test_filter_users_by_claims_returns_empty_for_nonexistent_user(self):
        """Test that filter_users_by_claims returns empty for nonexistent user."""
        users = self.backend.filter_users_by_claims(self.test_claims)

        self.assertEqual(users.count(), 0)


@override_settings(
    OIDC_ENABLED=True,
    AUTHENTICATION_BACKENDS=[
        "argus_du_libre.auth.OIDCAdminAuthenticationBackend",
        "django.contrib.auth.backends.ModelBackend",
    ],
)
class OIDCAuthenticationIntegrationTestCase(TestCase):
    """Integration tests for OIDC authentication."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = OIDCAdminAuthenticationBackend()

    def tearDown(self):
        """Clean up after tests."""
        User.objects.all().delete()

    @patch("mozilla_django_oidc.auth.OIDCAuthenticationBackend.verify_token")
    @patch("mozilla_django_oidc.auth.OIDCAuthenticationBackend.get_token")
    def test_full_authentication_flow_creates_admin_user(
        self, mock_get_token, mock_verify_token
    ):
        """Test full authentication flow creates admin user."""
        mock_get_token.return_value = {"id_token": "fake_token"}
        mock_verify_token.return_value = True

        claims = {
            "email": "newadmin@example.com",
            "preferred_username": "newadmin",
            "sub": "987654321",
        }

        # Create user through the backend
        user = self.backend.create_user(claims)

        # Verify user was created with correct attributes
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "newadmin@example.com")
        self.assertEqual(user.username, "newadmin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        # Verify user can be retrieved
        retrieved_user = User.objects.get(email="newadmin@example.com")
        self.assertEqual(retrieved_user, user)

    @patch("mozilla_django_oidc.auth.OIDCAuthenticationBackend.verify_token")
    @patch("mozilla_django_oidc.auth.OIDCAuthenticationBackend.get_token")
    def test_authentication_updates_existing_user(
        self, mock_get_token, mock_verify_token
    ):
        """Test authentication updates existing user."""
        mock_get_token.return_value = {"id_token": "fake_token"}
        mock_verify_token.return_value = True

        # Create initial user without admin privileges
        user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            is_staff=False,
            is_superuser=False,
        )

        claims = {
            "email": "existing@example.com",
            "preferred_username": "existinguser",
            "sub": "111111111",
        }

        # Update user through the backend
        updated_user = self.backend.update_user(user, claims)

        # Verify user was updated with admin privileges
        self.assertEqual(updated_user.email, "existing@example.com")
        self.assertTrue(updated_user.is_staff)
        self.assertTrue(updated_user.is_superuser)
