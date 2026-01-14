"""Views for public-facing pages."""

from collections import defaultdict
from decimal import Decimal

from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

from projects.models import Block, Field, MetricValue, Software


def home(request):
    """Homepage view showing the last 20 featured projects."""
    featured_projects = Software.objects.filter(
        state=Software.STATE_PUBLISHED, featured_at__isnull=False
    ).order_by("-featured_at")[:20]

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

    # Get most recent published analysis result for each field
    results = (
        software.analysis_results.filter(is_published=True)
        .select_related("field__category")
        .order_by("field_id", "-created_at")
        .distinct("field_id")
    )

    # Group results by category and calculate category scores
    categories_data = defaultdict(
        lambda: {"fields": {}, "total_weighted": 0, "total_weight": 0}
    )

    for result in results:
        category = result.field.category
        field = result.field

        # Get localized field name
        field_translation = field.get_translation(locale)
        field_name = field_translation.name if field_translation else str(field)

        # Add field score
        categories_data[category]["fields"][field.id] = {
            "field": field,
            "field_name": field_name,
            "score": result.score,
        }

        # Accumulate for weighted mean
        categories_data[category]["total_weighted"] += (
            float(result.score) * field.weight
        )
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
        category_name = (
            category_translation.name if category_translation else str(category)
        )

        # Convert fields dict to sorted list
        fields_list = sorted(
            data["fields"].values(),
            key=lambda x: (x["field"].weight, x["field"].id)
        )

        categories_with_scores.append(
            {
                "category": category,
                "category_name": category_name,
                "score": category_score,
                "fields": fields_list,
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

    # Get other published projects for comparison selector
    other_projects = (
        Software.objects.filter(state=Software.STATE_PUBLISHED)
        .exclude(id=software.id)
        .order_by("name")[:50]  # Limit to 50 for performance
    )

    context = {
        "software": software,
        "overview_block": overview_block,
        "categories_with_scores": categories_with_scores,
        "overall_score": overall_score,
        "other_projects": other_projects,
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


def search(request):
    """Search view for finding projects by name or content."""
    from django.db.models import Q

    query = request.GET.get("q", "").strip()
    results = []

    if query:
        # Get current locale
        locale = get_language()

        # Search in software name and block content for current locale
        results = (
            Software.objects.filter(
                Q(name__icontains=query)
                | Q(blocks__content__icontains=query, blocks__locale=locale),
                state=Software.STATE_PUBLISHED,
            )
            .distinct()
            .order_by("-featured_at", "-created_at")
        )

    context = {
        "query": query,
        "results": results,
    }

    return render(request, "public/search.html", context)


def compare(request):
    """Compare multiple projects side by side."""

    # Get project slugs from query parameter
    project_slugs = request.GET.get("projects", "").split(",")
    project_slugs = [slug.strip() for slug in project_slugs if slug.strip()]

    # Validate: must have 2-5 projects
    if len(project_slugs) < 2 or len(project_slugs) > 5:
        context = {
            "error": "Please select between 2 and 5 projects to compare.",
            "projects": [],
        }
        return render(request, "public/compare.html", context)

    # Fetch published projects
    projects = list(
        Software.objects.filter(slug__in=project_slugs, state=Software.STATE_PUBLISHED)
        .prefetch_related("tags", "analysis_results__field__category")
        .order_by("name")
    )

    # Validate: all slugs must exist and be published
    if len(projects) != len(project_slugs):
        context = {
            "error": "One or more projects not found or not published.",
            "projects": [],
        }
        return render(request, "public/compare.html", context)

    # Get current locale
    locale = get_language()

    # Calculate scores for each project
    projects_data = []
    all_categories = {}
    all_fields_by_category = defaultdict(set)

    for software in projects:
        # Get most recent published analysis result for each field
        results = (
            software.analysis_results.filter(is_published=True)
            .select_related("field__category")
            .order_by("field_id", "-created_at")
            .distinct("field_id")
        )

        # Group by category
        categories_data = defaultdict(
            lambda: {"fields": {}, "total_weighted": 0, "total_weight": 0}
        )

        for result in results:
            category = result.field.category
            field = result.field

            # Track all categories and fields
            all_categories[category.id] = category
            all_fields_by_category[category.id].add(field.id)

            # Store field score
            categories_data[category.id]["fields"][field.id] = {
                "field": field,
                "score": result.score,
            }

            # Accumulate for weighted mean
            categories_data[category.id]["total_weighted"] += (
                float(result.score) * field.weight
            )
            categories_data[category.id]["total_weight"] += field.weight

        # Calculate category scores
        category_scores = {}
        for cat_id, data in categories_data.items():
            if data["total_weight"] > 0:
                category_scores[cat_id] = Decimal(
                    str(data["total_weighted"] / data["total_weight"])
                ).quantize(Decimal("0.01"))
            else:
                category_scores[cat_id] = None

        # Calculate overall score
        overall_score = None
        if category_scores:
            total_weighted = 0
            total_weight = 0
            for cat_id, score in category_scores.items():
                if score is not None:
                    category = all_categories[cat_id]
                    total_weighted += float(score) * category.weight
                    total_weight += category.weight

            if total_weight > 0:
                overall_score = Decimal(str(total_weighted / total_weight)).quantize(
                    Decimal("0.01")
                )

        projects_data.append(
            {
                "software": software,
                "overall_score": overall_score,
                "categories_data": categories_data,
                "category_scores": category_scores,
            }
        )

    # Build comparison table structure
    categories_comparison = []

    # Sort categories by weight
    sorted_categories = sorted(all_categories.values(), key=lambda c: (c.weight, c.id))

    for category in sorted_categories:
        # Get localized category name
        category_translation = category.get_translation(locale)
        category_name = (
            category_translation.name if category_translation else str(category)
        )

        # Get category scores for each project
        category_scores_list = []
        for proj_data in projects_data:
            category_scores_list.append(proj_data["category_scores"].get(category.id))

        # Get all fields in this category

        field_ids = all_fields_by_category[category.id]
        fields = Field.objects.filter(id__in=field_ids).order_by("weight", "id")

        fields_comparison = []
        for field in fields:
            # Get localized field name
            field_translation = field.get_translation(locale)
            field_name = field_translation.name if field_translation else str(field)

            # Get field scores for each project
            field_scores_list = []
            for proj_data in projects_data:
                field_data = proj_data["categories_data"][category.id]["fields"].get(
                    field.id
                )
                field_scores_list.append(field_data["score"] if field_data else None)

            fields_comparison.append(
                {"field_name": field_name, "scores": field_scores_list}
            )

        categories_comparison.append(
            {
                "category_name": category_name,
                "category_scores": category_scores_list,
                "fields": fields_comparison,
            }
        )

    context = {
        "projects": projects,
        "projects_data": projects_data,
        "categories_comparison": categories_comparison,
        "error": None,
    }

    return render(request, "public/compare.html", context)


def field_metrics(request, software_slug, field_slug):
    """Field metrics detail view showing time-series charts for metrics."""
    import json

    from django.db.models import Prefetch
    from django.utils.safestring import mark_safe

    # Fetch software and field with 404 handling
    software = get_object_or_404(
        Software,
        slug=software_slug,
        state=Software.STATE_PUBLISHED,
    )

    # Get field with category prefetched
    field = get_object_or_404(
        Field.objects.select_related("category"),
        slug=field_slug,
    )

    # Get current locale
    locale = get_language()

    # Get localized names
    field_translation = field.get_translation(locale)
    field_name = field_translation.name if field_translation else str(field)

    category_translation = field.category.get_translation(locale)
    category_name = (
        category_translation.name if category_translation else str(field.category)
    )

    # Fetch metrics for this field with optimized prefetch
    metrics = field.metrics.filter(collection_enabled=True).prefetch_related(
        Prefetch(
            "values",
            queryset=MetricValue.objects.filter(software=software).order_by(
                "collected_at"
            ),
            to_attr="software_values",
        )
    )

    # Build metrics data structure for Chart.js
    metrics_data = []
    for metric in metrics:
        # Get metric translation
        metric_translation = metric.get_translation(locale)
        metric_name = metric_translation.name if metric_translation else str(metric)
        metric_description = (
            metric_translation.description if metric_translation else ""
        )

        # Get values from prefetched data
        values = metric.software_values

        # Only include metrics with data
        if values:
            # Convert to JSON-serializable format
            values_list = [
                {
                    "collected_at": v.collected_at.isoformat(),
                    "value": str(v.value),
                    "source": v.source,
                }
                for v in values
            ]

            metrics_data.append(
                {
                    "metric_id": metric.id,
                    "metric_name": metric_name,
                    "metric_description": metric_description,
                    "metric_slug": metric.slug,
                    "values": mark_safe(json.dumps(values_list)),
                }
            )

    context = {
        "software": software,
        "field": field,
        "field_name": field_name,
        "category_name": category_name,
        "metrics_data": metrics_data,
        "has_data": len(metrics_data) > 0,
    }

    return render(request, "public/field_metrics.html", context)


def about(request):
    """About page with project information."""
    return render(request, "public/about.html")
