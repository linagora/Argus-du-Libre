"""App configuration for Argus du Libre."""

from django.apps import AppConfig


class ArgusConfig(AppConfig):
    """Configuration for Argus du Libre application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "argus_du_libre"

    def ready(self):
        """Import admin configuration when the app is ready."""
        # Import admin to ensure custom admin site is registered
        from argus_du_libre import admin  # noqa: F401
