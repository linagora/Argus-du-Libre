"""Views for public-facing pages."""

from django.shortcuts import render

from projects.models import Software


def home(request):
    """Homepage view showing the last 20 featured projects."""
    featured_projects = (
        Software.objects.filter(
            state=Software.STATE_PUBLISHED, featured_at__isnull=False
        )
        .order_by("-featured_at")[:20]
    )

    context = {
        "featured_projects": featured_projects,
    }

    return render(request, "public/home.html", context)
