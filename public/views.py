"""Views for public-facing pages."""

from collections import defaultdict
from decimal import Decimal

from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from projects.models import Block, Software


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


def project_detail(request, slug):
    """Project detail view showing scores by category."""
    software = get_object_or_404(
        Software.objects.prefetch_related("tags", "analysis_results__field__category"),
        slug=slug,
        state=Software.STATE_PUBLISHED,
    )

    # Get current locale
    locale = get_language()

    # Get overview block for current locale
    overview_block = software.blocks.filter(
        kind=Block.KIND_OVERVIEW, locale=locale
    ).first()

    # Get all published analysis results for this software
    results = software.analysis_results.filter(is_published=True).select_related(
        "field__category"
    )

    # Group results by category and calculate category scores
    categories_data = defaultdict(lambda: {"fields": [], "total_weighted": 0, "total_weight": 0})

    for result in results:
        category = result.field.category
        field = result.field

        # Get localized field name
        field_translation = field.get_translation(locale)
        field_name = field_translation.name if field_translation else str(field)

        # Add field score
        categories_data[category]["fields"].append(
            {
                "field_name": field_name,
                "score": result.score,
            }
        )

        # Accumulate for weighted mean
        categories_data[category]["total_weighted"] += float(result.score) * field.weight
        categories_data[category]["total_weight"] += field.weight

    # Calculate category scores (weighted mean) and prepare final data
    categories_with_scores = []
    for category, data in categories_data.items():
        if data["total_weight"] > 0:
            category_score = Decimal(
                str(data["total_weighted"] / data["total_weight"])
            ).quantize(Decimal("0.01"))
        else:
            category_score = None

        # Get localized category name
        category_translation = category.get_translation(locale)
        category_name = category_translation.name if category_translation else str(category)

        categories_with_scores.append(
            {
                "category": category,
                "category_name": category_name,
                "score": category_score,
                "fields": data["fields"],
            }
        )

    # Sort by category weight
    categories_with_scores.sort(key=lambda x: (x["category"].weight, x["category"].id))

    # Calculate overall project score (weighted mean of category scores)
    overall_score = None
    if categories_with_scores:
        total_weighted = 0
        total_weight = 0
        for cat_data in categories_with_scores:
            if cat_data["score"] is not None:
                total_weighted += float(cat_data["score"]) * cat_data["category"].weight
                total_weight += cat_data["category"].weight

        if total_weight > 0:
            overall_score = Decimal(str(total_weighted / total_weight)).quantize(
                Decimal("0.01")
            )

    context = {
        "software": software,
        "overview_block": overview_block,
        "categories_with_scores": categories_with_scores,
        "overall_score": overall_score,
    }

    return render(request, "public/project_detail.html", context)

def tag_detail(request, slug):
    """Tag detail view showing all published projects with this tag."""
    from projects.models import Tag

    tag = get_object_or_404(Tag, slug=slug)

    # Get all published projects with this tag
    projects = tag.softwares.filter(state=Software.STATE_PUBLISHED).order_by(
        "-featured_at", "-created_at"
    )

    context = {
        "tag": tag,
        "projects": projects,
    }

    return render(request, "public/tag_detail.html", context)
