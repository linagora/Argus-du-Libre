"""Custom admin site configuration."""

from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect


class OIDCAdminSite(admin.AdminSite):
    """Custom admin site that redirects to OIDC authentication when enabled."""

    def login(self, request, extra_context=None):
        """Override login to redirect to OIDC when enabled."""
        if settings.OIDC_ENABLED:
            # Redirect to OIDC authentication
            return redirect("oidc_authentication_init")
        # Fall back to default login
        return super().login(request, extra_context)


# Create custom admin site instance
admin_site = OIDCAdminSite(name="admin")

# Replace the default admin site
admin.site = admin_site
admin.sites.site = admin_site
