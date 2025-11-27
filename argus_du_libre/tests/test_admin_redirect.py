"""Tests for admin OIDC redirect behavior."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(
    OIDC_ENABLED=True,
    AUTHENTICATION_BACKENDS=["argus_du_libre.auth.OIDCAdminAuthenticationBackend"],
)
class AdminOIDCRedirectTestCase(TestCase):
    """Test cases for admin OIDC redirect when OIDC is enabled."""

    def test_admin_redirects_to_oidc_when_not_authenticated(self):
        """Test that /admin redirects to OIDC authentication when user is not logged in."""
        # First, /admin/ redirects to /admin/login/
        response = self.client.get("/admin/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

        # Then, /admin/login/ redirects to OIDC
        response = self.client.get("/admin/login/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("oidc_authentication_init"))

    def test_admin_login_page_redirects_to_oidc(self):
        """Test that /admin/login/ redirects to OIDC authentication."""
        response = self.client.get("/admin/login/", follow=False)

        # Should redirect to OIDC authentication
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("oidc_authentication_init"))

    def test_admin_accessible_when_authenticated(self):
        """Test that authenticated users can access admin."""
        user = User.objects.create_user(
            username="testadmin",
            email="testadmin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)

        # Access a specific admin page (user change list)
        response = self.client.get("/admin/auth/user/")

        # Should show admin page (or redirect to /admin/ index)
        self.assertIn(response.status_code, [200, 302])
        # If redirected, should not be to login
        if response.status_code == 302:
            self.assertNotIn("login", response.url)


@override_settings(
    OIDC_ENABLED=False,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class AdminStandardLoginTestCase(TestCase):
    """Test cases for admin standard login when OIDC is disabled."""

    def test_admin_shows_login_form_when_oidc_disabled(self):
        """Test that /admin shows standard login form when OIDC is disabled."""
        response = self.client.get("/admin/login/", follow=True)

        # Should show login form
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username")
        self.assertContains(response, "Password")

    def test_admin_login_works_with_username_password(self):
        """Test that username/password login works when OIDC is disabled."""
        user = User.objects.create_user(
            username="testadmin",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Perform login
        login_successful = self.client.login(
            username="testadmin", password="testpass123"
        )
        self.assertTrue(login_successful)

        # Access admin to verify authentication
        response = self.client.get("/admin/")

        # Should be authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user, user)

    def test_admin_accessible_when_authenticated_without_oidc(self):
        """Test that authenticated users can access admin when OIDC is disabled."""
        user = User.objects.create_user(
            username="testadmin",
            email="testadmin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)

        # Access a specific admin page (user change list)
        response = self.client.get("/admin/auth/user/")

        # Should show admin page (or redirect to /admin/ index)
        self.assertIn(response.status_code, [200, 302])
        # If redirected, should not be to login
        if response.status_code == 302:
            self.assertNotIn("login", response.url)
