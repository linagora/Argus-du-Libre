"""Custom OIDC authentication backend for admin users."""

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class OIDCAdminAuthenticationBackend(OIDCAuthenticationBackend):
    """Custom OIDC authentication backend that creates admin users."""

    def create_user(self, claims):
        """Create a user with admin and staff privileges."""
        email = claims.get("email")
        username = claims.get("preferred_username", email)

        user = self.UserModel.objects.create_user(
            username=username,
            email=email,
        )

        # Make the user an admin and staff member
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return user

    def update_user(self, user, claims):
        """Update user information from OIDC claims."""
        email = claims.get("email")
        if email and user.email != email:
            user.email = email

        # Ensure the user remains an admin
        if not user.is_staff:
            user.is_staff = True
        if not user.is_superuser:
            user.is_superuser = True

        user.save()
        return user

    def filter_users_by_claims(self, claims):
        """Filter users by email from OIDC claims."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()

        return self.UserModel.objects.filter(email__iexact=email)
