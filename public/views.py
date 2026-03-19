"""Views for public-facing pages."""

import json
from collections import defaultdict
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Count
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.views.decorators.http import require_POST

from projects.models import (
    FEEDBACK_FIELD_SLUGS,
    Block,
    CostFeedbackEntry,
    CostFeedbackSubmission,
    Field,
    MetricValue,
    Software,
    Tag,
    TagOpinion,
)
from public.aggregator import CostScoreAggregator
from public.forms import CostFeedbackForm


def _calculate_overall_score(software):
    """Calculate overall weighted score (0-100) from prefetched analysis results."""
    # Get most recent published result per field
    latest_by_field = {}
    for result in software.analysis_results.all():
        if not result.is_published:
            continue
        fid = result.field_id
        if (
            fid not in latest_by_field
            or result.created_at > latest_by_field[fid].created_at
        ):
            latest_by_field[fid] = result

    if not latest_by_field:
        return None

    # Calculate category scores (weighted mean of field scores)
    cat_data = defaultdict(lambda: {"tw": 0, "w": 0, "cat": None})
    for result in latest_by_field.values():
        cat = result.field.category
        cat_data[cat.id]["cat"] = cat
        cat_data[cat.id]["tw"] += float(result.score) * result.field.weight
        cat_data[cat.id]["w"] += result.field.weight

    # Overall score (weighted mean of category scores) on 1-5 scale
    total_tw = 0
    total_w = 0
    for d in cat_data.values():
        if d["w"] > 0:
            cat_score = d["tw"] / d["w"]
            total_tw += cat_score * d["cat"].weight
            total_w += d["cat"].weight

    if total_w > 0:
        return Decimal(str(total_tw / total_w)).quantize(Decimal("0.01"))
    return None


def home(request):
    """Homepage view showing the last 20 featured projects."""
    locale = get_language()

    featured_projects = (
        Software.objects.filter(
            state=Software.STATE_PUBLISHED, featured_at__isnull=False
        )
        .prefetch_related("analysis_results__field__category", "blocks")
        .order_by("-featured_at")[:20]
    )

    featured_list = _build_project_list(featured_projects, locale)

    # Get all published software grouped by first letter
    all_projects = Software.objects.filter(state=Software.STATE_PUBLISHED).order_by(
        Lower("name")
    )
    projects_by_letter = defaultdict(list)
    for project in all_projects:
        first_letter = project.name[0].upper() if project.name else "#"
        if not first_letter.isalpha():
            first_letter = "#"
        projects_by_letter[first_letter].append(project)

    # Sort letters alphabetically, with # at the end
    sorted_letters = sorted(projects_by_letter.keys(), key=lambda x: (x == "#", x))
    projects_by_letter_sorted = [
        (letter, projects_by_letter[letter]) for letter in sorted_letters
    ]

    context = {
        "featured_projects": featured_list,
        "projects_by_letter": projects_by_letter_sorted,
    }

    return render(request, "public/home.html", context)


def _build_project_detail_context(request, software):
    """
    Build the context dict for the project_detail template.
    Called by both `project_detail` (GET) and `_render_project_detail_with_form`
    (POST error re-render) so context logic is not duplicated.
    """
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

        field_translation = field.get_translation(locale)
        field_name = field_translation.name if field_translation else str(field)
        field_description = field_translation.description if field_translation else ""

        categories_data[category]["fields"][field.id] = {
            "field": field,
            "field_name": field_name,
            "field_description": field_description,
            "score": result.score,
        }

        categories_data[category]["total_weighted"] += (
            float(result.score) * field.weight
        )
        categories_data[category]["total_weight"] += field.weight

    categories_with_scores = []
    for category, data in categories_data.items():
        if data["total_weight"] > 0:
            category_score = Decimal(
                str(data["total_weighted"] / data["total_weight"])
            ).quantize(Decimal("0.01"))
        else:
            category_score = None

        category_translation = category.get_translation(locale)
        category_name = (
            category_translation.name if category_translation else str(category)
        )

        fields_list = sorted(
            data["fields"].values(),
            key=lambda x: (x["field"].weight, x["field"].id),
        )

        categories_with_scores.append(
            {
                "category": category,
                "category_name": category_name,
                "score": category_score,
                "fields": fields_list,
            }
        )

    categories_with_scores.sort(key=lambda x: (x["category"].weight, x["category"].id))

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

    tag_opinion_sections = []
    tag_opinions = TagOpinion.objects.filter(
        tag__in=software.tags.all(), locale=locale
    ).select_related("tag")
    for opinion in tag_opinions:
        related_qs = (
            opinion.tag.softwares.filter(state=Software.STATE_PUBLISHED)
            .exclude(id=software.id)
            .prefetch_related("analysis_results__field__category", "blocks")
            .order_by("-featured_at", "-created_at")[:8]
        )
        related_projects = list(related_qs)
        show_more_link = len(related_projects) == 8
        if show_more_link:
            related_projects = related_projects[:7]
        tag_opinion_sections.append(
            {
                "tag": opinion.tag,
                "opinion_content": opinion.content,
                "projects": _build_project_list(related_projects, locale),
                "show_more_link": show_more_link,
            }
        )

    # Build costs_fields with translated names for template rendering
    raw_feedback_fields = Field.objects.filter(slug__in=FEEDBACK_FIELD_SLUGS)
    costs_fields = []
    for cf in raw_feedback_fields:
        translation = cf.get_translation(locale)
        costs_fields.append(
            {
                "field": cf,
                "name": translation.name if translation else cf.slug,
            }
        )

    # 5 most recent submissions with a general comment
    recent_submissions = list(
        software.cost_feedback_submissions.exclude(general_comment__isnull=True)
        .exclude(general_comment="")
        .order_by("-created_at")[:5]
    )

    return {
        "software": software,
        "overview_block": overview_block,
        "categories_with_scores": categories_with_scores,
        "overall_score": overall_score,
        "tag_opinion_sections": tag_opinion_sections,
        "costs_fields": costs_fields,
        "recent_submissions": recent_submissions,
    }


def project_detail(request, slug):
    """Project detail view showing scores by category."""
    software = get_object_or_404(
        Software.objects.prefetch_related("tags", "analysis_results__field__category"),
        slug=slug,
        state=Software.STATE_PUBLISHED,
    )
    context = _build_project_detail_context(request, software)
    locale = get_language()
    raw_fields = [d["field"] for d in context["costs_fields"]]
    context["cost_feedback_form"] = CostFeedbackForm(
        initial={"locale": locale}, fields=raw_fields, locale=locale
    )
    context["feedback_created"] = request.GET.get("feedback") == "created"
    return render(request, "public/project_detail.html", context)


def tags_list(request):
    """List all tags that have at least one published project."""

    tags = (
        Tag.objects.annotate(
            project_count=Count(
                "softwares",
                filter=models.Q(softwares__state=Software.STATE_PUBLISHED),
            )
        )
        .filter(project_count__gt=0)
        .order_by("name")
    )

    context = {
        "tags": tags,
    }

    return render(request, "public/tags_list.html", context)


def _build_project_list(projects, locale):
    """Build a list of dicts with project, score, and overview for card display."""
    result = []
    for project in projects:
        overview_text = ""
        for block in project.blocks.all():
            if block.kind == Block.KIND_OVERVIEW and block.locale == locale:
                overview_text = block.content
                break

        result.append(
            {
                "project": project,
                "score": _calculate_overall_score(project),
                "overview": overview_text,
            }
        )
    return result


def tag_detail(request, slug):
    """Tag detail view showing all published projects with this tag."""

    tag = get_object_or_404(Tag, slug=slug)
    locale = get_language()

    # Get opinion for current locale
    opinion = tag.opinions.filter(locale=locale).first()

    # Get all published projects with this tag
    projects = (
        tag.softwares.filter(state=Software.STATE_PUBLISHED)
        .prefetch_related("analysis_results__field__category", "blocks")
        .order_by("-featured_at", "-created_at")
    )

    context = {
        "tag": tag,
        "opinion": opinion,
        "projects": _build_project_list(projects, locale),
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
        projects = (
            Software.objects.filter(
                Q(name__icontains=query)
                | Q(blocks__content__icontains=query, blocks__locale=locale),
                state=Software.STATE_PUBLISHED,
            )
            .prefetch_related("analysis_results__field__category", "blocks")
            .distinct()
            .order_by("-featured_at", "-created_at")
        )
        results = _build_project_list(projects, locale)

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

    # Build comparison table structure and JSON data for client-side recalculation
    categories_comparison = []
    comparison_data = {"categories": []}

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
        fields_json = []
        for field in fields:
            # Get localized field name
            field_translation = field.get_translation(locale)
            field_name = field_translation.name if field_translation else str(field)

            # Get field scores for each project
            field_scores_list = []
            field_scores_json = []
            for proj_data in projects_data:
                field_data = proj_data["categories_data"][category.id]["fields"].get(
                    field.id
                )
                field_scores_list.append(field_data["score"] if field_data else None)
                field_scores_json.append(
                    float(field_data["score"]) if field_data else None
                )

            field_description = (
                field_translation.description
                if field_translation and field_translation.description
                else ""
            )

            fields_comparison.append(
                {
                    "field_name": field_name,
                    "field_id": field.id,
                    "field_description": field_description,
                    "scores": field_scores_list,
                }
            )
            fields_json.append({"weight": field.weight, "scores": field_scores_json})

        categories_comparison.append(
            {
                "category_name": category_name,
                "category_scores": category_scores_list,
                "fields": fields_comparison,
            }
        )
        comparison_data["categories"].append(
            {"weight": category.weight, "fields": fields_json}
        )

    context = {
        "projects": projects,
        "projects_data": projects_data,
        "categories_comparison": categories_comparison,
        "comparison_data_json": mark_safe(json.dumps(comparison_data)),
        "error": None,
    }

    return render(request, "public/compare.html", context)


def field_metrics(request, software_slug, field_slug):
    """Field metrics detail view showing time-series charts for metrics."""

    from django.db.models import Prefetch

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


def scores_help(request):
    """Help page listing scoring methodology for all fields."""
    from projects.models import Category

    locale = get_language()

    categories = Category.objects.prefetch_related("fields__translations").order_by(
        "weight", "id"
    )

    categories_data = []
    for category in categories:
        category_translation = category.get_translation(locale)
        category_name = (
            category_translation.name if category_translation else str(category)
        )

        fields_data = []
        for field in category.fields.order_by("weight", "id"):
            field_translation = field.get_translation(locale)
            field_name = field_translation.name if field_translation else str(field)
            field_description = (
                field_translation.description if field_translation else ""
            )

            fields_data.append(
                {
                    "field": field,
                    "field_name": field_name,
                    "field_description": field_description,
                }
            )

        if fields_data:
            categories_data.append(
                {
                    "category": category,
                    "category_name": category_name,
                    "fields": fields_data,
                }
            )

    context = {
        "categories_data": categories_data,
    }

    return render(request, "public/scores_help.html", context)


def about(request):
    """About page with project information."""
    return render(request, "public/about.html")


@require_POST
def create_cost_feedback(request, slug):
    """POST-only: validate and persist crowd cost ratings, then redirect."""
    software = get_object_or_404(Software, slug=slug, state=Software.STATE_PUBLISHED)
    costs_fields = list(Field.objects.filter(slug__in=FEEDBACK_FIELD_SLUGS))
    form = CostFeedbackForm(request.POST, fields=costs_fields)

    if not form.is_valid():
        return _render_project_detail_with_form(request, software, form)

    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")

    with transaction.atomic():
        submission = CostFeedbackSubmission.objects.create(
            software=software,
            locale=form.cleaned_data["locale"],
            general_comment=form.cleaned_data.get("general_comment") or None,
            ip_address=ip,
        )
        for field in costs_fields:
            score = int(form.cleaned_data[f"score_{field.slug}"])
            CostFeedbackEntry.objects.create(
                submission=submission,
                field=field,
                score=score,
            )

    CostScoreAggregator(software).run()

    return redirect(
        reverse("public:project_detail", kwargs={"slug": slug}) + "?feedback=created"
    )


def _render_project_detail_with_form(request, software, form):
    """Re-render project_detail when the cost feedback form has errors."""
    context = _build_project_detail_context(request, software)
    context["cost_feedback_form"] = form
    context["feedback_created"] = False
    return render(request, "public/project_detail.html", context)
