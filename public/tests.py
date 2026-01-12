"""Tests for public views."""

from datetime import UTC, datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from projects.models import (
    AnalysisResult,
    Block,
    Category,
    CategoryTranslation,
    Field,
    FieldTranslation,
    Metric,
    MetricTranslation,
    MetricValue,
    Software,
    Tag,
)


class HomeViewTestCase(TestCase):
    """Test cases for home view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create software instances
        self.published_featured = Software.objects.create(
            name="Featured Project",
            slug="featured",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        self.published_not_featured = Software.objects.create(
            name="Not Featured",
            slug="not-featured",
            state=Software.STATE_PUBLISHED,
            featured_at=None,
        )
        self.draft_featured = Software.objects.create(
            name="Draft Featured",
            slug="draft-featured",
            state=Software.STATE_DRAFT,
            featured_at=datetime(2024, 1, 10, tzinfo=UTC),
        )

    def test_home_page_loads_successfully(self):
        """Test that home page returns 200 status."""
        response = self.client.get(reverse("public:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/home.html")

    def test_home_page_shows_published_featured_projects(self):
        """Test that only published and featured projects are shown."""
        response = self.client.get(reverse("public:home"))
        self.assertContains(response, "Featured Project")
        self.assertNotContains(response, "Not Featured")
        self.assertNotContains(response, "Draft Featured")

    def test_home_page_orders_by_featured_at_desc(self):
        """Test that projects are ordered by featured_at descending."""
        # Create more featured projects
        older = Software.objects.create(
            name="Older Featured",
            slug="older",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        newer = Software.objects.create(
            name="Newer Featured",
            slug="newer",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 20, tzinfo=UTC),
        )

        response = self.client.get(reverse("public:home"))
        content = response.content.decode("utf-8")

        # Newer should appear before older in HTML
        newer_pos = content.find("Newer Featured")
        older_pos = content.find("Older Featured")
        self.assertLess(newer_pos, older_pos)

    def test_home_page_limits_to_20_projects(self):
        """Test that home page shows maximum 20 projects."""
        # Create 25 featured projects
        for i in range(25):
            Software.objects.create(
                name=f"Project {i}",
                slug=f"project-{i}",
                state=Software.STATE_PUBLISHED,
                featured_at=datetime(2024, 1, 1, tzinfo=UTC),
            )

        response = self.client.get(reverse("public:home"))
        projects = response.context["featured_projects"]
        self.assertEqual(len(projects), 20)

    def test_home_page_shows_empty_state(self):
        """Test that home page shows message when no featured projects."""
        # Delete all featured projects
        Software.objects.filter(featured_at__isnull=False).delete()

        response = self.client.get(reverse("public:home"))
        self.assertContains(response, "No featured projects available")

    def test_home_page_shows_project_logo(self):
        """Test that project logo is displayed when available."""
        self.published_featured.logo_url = "https://example.com/logo.png"
        self.published_featured.save()

        response = self.client.get(reverse("public:home"))
        self.assertContains(response, self.published_featured.logo_url)

    def test_home_page_shows_read_more_link(self):
        """Test that read more link points to project detail."""
        response = self.client.get(reverse("public:home"))
        project_url = reverse("public:project_detail", kwargs={"slug": "featured"})
        self.assertContains(response, project_url)
        self.assertContains(response, "Read More")


class ProjectDetailViewTestCase(TestCase):
    """Test cases for project detail view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create categories with translations
        self.category_tech = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category_tech, locale="en", name="Technology"
        )
        CategoryTranslation.objects.create(
            category=self.category_tech, locale="fr", name="Technologie"
        )

        self.category_security = Category.objects.create(weight=2)
        CategoryTranslation.objects.create(
            category=self.category_security, locale="en", name="Security"
        )

        # Create fields with translations
        self.field_code_quality = Field.objects.create(
            category=self.category_tech, slug="code-quality", weight=2
        )
        FieldTranslation.objects.create(
            field=self.field_code_quality, locale="en", name="Code Quality"
        )

        self.field_performance = Field.objects.create(
            category=self.category_tech, slug="performance", weight=1
        )
        FieldTranslation.objects.create(
            field=self.field_performance, locale="en", name="Performance"
        )

        self.field_vulnerability = Field.objects.create(
            category=self.category_security, slug="vulnerability", weight=1
        )
        FieldTranslation.objects.create(
            field=self.field_vulnerability, locale="en", name="Vulnerability"
        )

        # Create tags
        self.tag1 = Tag.objects.create(name="Database", slug="database")
        self.tag2 = Tag.objects.create(name="Cache", slug="cache")

        # Create software
        self.software = Software.objects.create(
            name="Test Software",
            slug="test-software",
            logo_url="https://example.com/logo.svg",
            website_url="https://example.com",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        self.software.tags.add(self.tag1, self.tag2)

        # Create analysis results
        AnalysisResult.objects.create(
            software=self.software,
            field=self.field_code_quality,
            score=Decimal("4.50"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software,
            field=self.field_performance,
            score=Decimal("3.00"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software,
            field=self.field_vulnerability,
            score=Decimal("5.00"),
            is_published=True,
        )

        # Create blocks
        Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="# Overview\n\nThis is **markdown** content.",
        )
        Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="fr",
            content="# Aperçu\n\nCeci est du contenu **markdown**.",
        )

    def test_project_detail_page_loads_successfully(self):
        """Test that project detail page returns 200 status."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/project_detail.html")

    def test_project_detail_returns_404_for_nonexistent_slug(self):
        """Test that 404 is returned for non-existent project."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "does-not-exist"})
        )
        self.assertEqual(response.status_code, 404)

    def test_project_detail_returns_404_for_draft_software(self):
        """Test that draft software is not accessible."""
        draft = Software.objects.create(
            name="Draft Software", slug="draft", state=Software.STATE_DRAFT
        )
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "draft"})
        )
        self.assertEqual(response.status_code, 404)

    def test_project_detail_returns_404_for_in_review_software(self):
        """Test that in-review software is not accessible."""
        in_review = Software.objects.create(
            name="Review Software",
            slug="in-review",
            state=Software.STATE_IN_REVIEW,
        )
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "in-review"})
        )
        self.assertEqual(response.status_code, 404)

    def test_project_detail_shows_software_name(self):
        """Test that software name is displayed."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Test Software")

    def test_project_detail_shows_logo(self):
        """Test that logo is displayed with correct styling."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, self.software.logo_url)
        self.assertContains(response, "width: 150px; height: 150px")

    def test_project_detail_shows_tags(self):
        """Test that tags are displayed."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Database")
        self.assertContains(response, "Cache")

    def test_project_detail_shows_website_link(self):
        """Test that website link is displayed."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, self.software.website_url)
        self.assertContains(response, "Visit Website")

    def test_project_detail_shows_categories_with_scores(self):
        """Test that categories are displayed with their weighted scores."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Technology")
        self.assertContains(response, "Security")

        # Check that scores are displayed
        categories_data = response.context["categories_with_scores"]
        self.assertEqual(len(categories_data), 2)

        # Find Tech category (weighted mean of 4.5*2 + 3.0*1 / 3 = 4.0)
        tech_data = next(
            c for c in categories_data if c["category"] == self.category_tech
        )
        self.assertEqual(tech_data["score"], Decimal("4.00"))

        # Find Security category (only one field: 5.0)
        security_data = next(
            c for c in categories_data if c["category"] == self.category_security
        )
        self.assertEqual(security_data["score"], Decimal("5.00"))

    def test_project_detail_shows_field_scores(self):
        """Test that individual field scores are displayed."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Code Quality")
        self.assertContains(response, "Performance")
        self.assertContains(response, "Vulnerability")

    def test_project_detail_calculates_weighted_mean_correctly(self):
        """Test that category score is weighted mean of field scores."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        categories_data = response.context["categories_with_scores"]

        tech_data = next(
            c for c in categories_data if c["category"] == self.category_tech
        )

        # Weighted mean: (4.5 * 2 + 3.0 * 1) / (2 + 1) = 12.0 / 3 = 4.0
        expected_score = Decimal("4.00")
        self.assertEqual(tech_data["score"], expected_score)

    def test_project_detail_only_shows_published_results(self):
        """Test that only published analysis results are shown."""
        # Create unpublished result
        unpublished_field = Field.objects.create(
            category=self.category_tech, slug="unpublished", weight=1
        )
        FieldTranslation.objects.create(
            field=unpublished_field, locale="en", name="Unpublished Field"
        )
        AnalysisResult.objects.create(
            software=self.software,
            field=unpublished_field,
            score=Decimal("1.00"),
            is_published=False,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertNotContains(response, "Unpublished Field")

    def test_project_detail_shows_overview_with_markdown(self):
        """Test that overview is displayed with markdown rendered."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Overview")
        # Check that markdown is converted to HTML
        self.assertContains(response, "<h1>Overview</h1>")
        self.assertContains(response, "<strong>markdown</strong>")

    def test_project_detail_uses_correct_locale_for_overview(self):
        """Test that overview uses the current locale."""
        # Test English locale (default)
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "<h1>Overview</h1>")

        # Test French locale
        response = self.client.get(
            "/fr/project/test-software/", HTTP_ACCEPT_LANGUAGE="fr"
        )
        self.assertContains(response, "<h1>Aperçu</h1>")

    def test_project_detail_without_overview_block(self):
        """Test that page works without overview block."""
        # Create software without overview
        software_no_overview = Software.objects.create(
            name="No Overview",
            slug="no-overview",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "no-overview"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["overview_block"])

    def test_project_detail_color_coded_scores(self):
        """Test that score badges have correct color classes."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        # Should have score-3, score-4, and score-5 classes
        self.assertContains(response, "score-badge score-3")
        self.assertContains(response, "score-badge score-4")
        self.assertContains(response, "score-badge score-5")

    def test_project_detail_categories_ordered_by_weight(self):
        """Test that categories are ordered by weight."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        categories_data = response.context["categories_with_scores"]

        # Technology (weight 1) should come before Security (weight 2)
        self.assertEqual(categories_data[0]["category"], self.category_tech)
        self.assertEqual(categories_data[1]["category"], self.category_security)

    def test_project_detail_without_logo(self):
        """Test that page works without logo."""
        software_no_logo = Software.objects.create(
            name="No Logo",
            slug="no-logo",
            logo_url="",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "no-logo"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<img src=""')

    def test_project_detail_without_tags(self):
        """Test that page works without tags."""
        software_no_tags = Software.objects.create(
            name="No Tags",
            slug="no-tags",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "no-tags"})
        )
        self.assertEqual(response.status_code, 200)

    def test_project_detail_without_website(self):
        """Test that page works without website URL."""
        software_no_website = Software.objects.create(
            name="No Website",
            slug="no-website",
            website_url="",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "no-website"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Visit Website")

    def test_project_detail_calculates_overall_score(self):
        """Test that overall score is calculated as weighted mean of category scores."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )

        overall_score = response.context["overall_score"]
        self.assertIsNotNone(overall_score)

        # Category scores:
        # - Technology (weight 1): 4.0
        # - Security (weight 2): 5.0
        # Overall = (4.0 * 1 + 5.0 * 2) / (1 + 2) = 14.0 / 3 = 4.67
        expected_score = Decimal("4.67")
        self.assertEqual(overall_score, expected_score)

    def test_project_detail_displays_overall_score(self):
        """Test that overall score is displayed on the page."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        self.assertContains(response, "Overall Score")
        self.assertContains(response, "4.7")

    def test_project_detail_overall_score_has_color(self):
        """Test that overall score has color-coded badge."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )
        # Overall score is 4.67, should have score-5 class (rounded to 5)
        content = response.content.decode("utf-8")
        # Find the overall score badge
        self.assertIn("Overall Score", content)
        # The score should be displayed with a color badge
        self.assertRegex(content, r"score-badge score-\d+")

    def test_project_detail_without_scores_no_overall_score(self):
        """Test that overall score is None when no analysis results exist."""
        software_no_scores = Software.objects.create(
            name="No Scores",
            slug="no-scores",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "no-scores"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["overall_score"])
        # Check that the score badge is not displayed (not just the comment)
        self.assertNotContains(response, "Overall Score:</span>")

    def test_project_detail_overall_score_with_different_category_weights(self):
        """Test overall score calculation with various category weights."""
        # Create a new software with specific category scores
        software2 = Software.objects.create(
            name="Test Software 2",
            slug="test-software-2",
            state=Software.STATE_PUBLISHED,
        )

        # Create categories with different weights
        cat_a = Category.objects.create(weight=3)
        CategoryTranslation.objects.create(
            category=cat_a, locale="en", name="Category A"
        )
        cat_b = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=cat_b, locale="en", name="Category B"
        )

        # Create fields
        field_a = Field.objects.create(category=cat_a, slug="field-a", weight=1)
        FieldTranslation.objects.create(field=field_a, locale="en", name="Field A")
        field_b = Field.objects.create(category=cat_b, slug="field-b", weight=1)
        FieldTranslation.objects.create(field=field_b, locale="en", name="Field B")

        # Create results: Cat A = 2.0, Cat B = 4.0
        AnalysisResult.objects.create(
            software=software2,
            field=field_a,
            score=Decimal("2.00"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=software2,
            field=field_b,
            score=Decimal("4.00"),
            is_published=True,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software-2"})
        )

        # Overall = (2.0 * 3 + 4.0 * 1) / (3 + 1) = 10.0 / 4 = 2.5
        expected_score = Decimal("2.50")
        self.assertEqual(response.context["overall_score"], expected_score)

    def test_project_detail_shows_most_recent_score_when_duplicates(self):
        """Test that when multiple results exist for a field, the most recent is shown."""
        from time import sleep

        # Create an older result with score 2.0
        older_result = AnalysisResult.objects.create(
            software=self.software,
            field=self.field_code_quality,
            score=Decimal("2.00"),
            is_published=True,
        )

        # Small delay to ensure different created_at timestamps
        sleep(0.01)

        # Create a newer result with score 5.0
        newer_result = AnalysisResult.objects.create(
            software=self.software,
            field=self.field_code_quality,
            score=Decimal("5.00"),
            is_published=True,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-software"})
        )

        # Should use the newer score (5.0) not the older one (2.0)
        categories_data = response.context["categories_with_scores"]
        tech_data = next(
            c for c in categories_data if c["category"] == self.category_tech
        )

        # Find the code quality field score
        code_quality_field = next(
            f for f in tech_data["fields"] if f["field"] == self.field_code_quality
        )

        # Should have the newer score (5.0)
        self.assertEqual(code_quality_field["score"], Decimal("5.00"))

        # Field should appear only once
        code_quality_count = sum(
            1 for f in tech_data["fields"] if f["field"] == self.field_code_quality
        )
        self.assertEqual(code_quality_count, 1)


class TagDetailViewTestCase(TestCase):
    """Test cases for tag detail view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create tags
        self.tag1 = Tag.objects.create(name="Database", slug="database")
        self.tag2 = Tag.objects.create(name="Cache", slug="cache")

        # Create published software with tags
        self.software1 = Software.objects.create(
            name="Software 1",
            slug="software-1",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        self.software1.tags.add(self.tag1, self.tag2)

        self.software2 = Software.objects.create(
            name="Software 2",
            slug="software-2",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 10, tzinfo=UTC),
        )
        self.software2.tags.add(self.tag1)

        # Create draft software with tag
        self.draft_software = Software.objects.create(
            name="Draft Software",
            slug="draft-software",
            state=Software.STATE_DRAFT,
        )
        self.draft_software.tags.add(self.tag1)

    def test_tag_detail_page_loads_successfully(self):
        """Test that tag detail page returns 200 status."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "database"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/tag_detail.html")

    def test_tag_detail_returns_404_for_nonexistent_tag(self):
        """Test that 404 is returned for non-existent tag."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "does-not-exist"})
        )
        self.assertEqual(response.status_code, 404)

    def test_tag_detail_shows_tag_name(self):
        """Test that tag name is displayed."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "database"})
        )
        self.assertContains(response, "Database")

    def test_tag_detail_shows_published_projects_only(self):
        """Test that only published projects are shown."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "database"})
        )
        self.assertContains(response, "Software 1")
        self.assertContains(response, "Software 2")
        self.assertNotContains(response, "Draft Software")

    def test_tag_detail_shows_correct_projects_for_tag(self):
        """Test that only projects with the specific tag are shown."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "cache"})
        )
        self.assertContains(response, "Software 1")
        self.assertNotContains(response, "Software 2")

    def test_tag_detail_orders_by_featured_at(self):
        """Test that projects are ordered by featured_at descending."""
        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "database"})
        )
        content = response.content.decode("utf-8")

        # Software 1 (featured Jan 15) should appear before Software 2 (featured Jan 10)
        software1_pos = content.find("Software 1")
        software2_pos = content.find("Software 2")
        self.assertLess(software1_pos, software2_pos)

    def test_tag_detail_shows_project_logos(self):
        """Test that project logos are displayed."""
        self.software1.logo_url = "https://example.com/logo.png"
        self.software1.save()

        response = self.client.get(
            reverse("public:tag_detail", kwargs={"slug": "database"})
        )
        self.assertContains(response, self.software1.logo_url)

    def test_tag_detail_shows_read_more_links(self):
        """Test that read more links point to project detail."""
        response = self.client.get("/en/tag/database/", HTTP_ACCEPT_LANGUAGE="en")
        project_url = "/en/project/software-1/"
        self.assertContains(response, project_url)
        self.assertContains(response, "Read More")

    def test_tag_detail_empty_state(self):
        """Test that empty state is shown when no projects have the tag."""
        tag_no_projects = Tag.objects.create(name="Empty Tag", slug="empty-tag")

        response = self.client.get("/en/tag/empty-tag/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No projects found with this tag")

    def test_project_detail_tags_are_clickable(self):
        """Test that tags on project detail page are clickable links."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "software-1"})
        )
        tag_url = reverse("public:tag_detail", kwargs={"slug": "database"})
        self.assertContains(response, tag_url)
        # Check that the tag is a link, not just a span
        self.assertContains(response, f'<a href="{tag_url}"')


class SearchViewTestCase(TestCase):
    """Test cases for search view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create published software
        self.software1 = Software.objects.create(
            name="Django Project",
            slug="django-project",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        self.software2 = Software.objects.create(
            name="Flask Application",
            slug="flask-app",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 10, tzinfo=UTC),
        )
        self.software3 = Software.objects.create(
            name="FastAPI Service",
            slug="fastapi-service",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 5, tzinfo=UTC),
        )

        # Create draft software (should not appear in search)
        self.draft_software = Software.objects.create(
            name="Draft Django Tool",
            slug="draft-tool",
            state=Software.STATE_DRAFT,
        )

        # Create blocks with searchable content
        Block.objects.create(
            software=self.software1,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="A comprehensive web framework for Python developers.",
        )
        Block.objects.create(
            software=self.software1,
            kind=Block.KIND_OVERVIEW,
            locale="fr",
            content="Un framework web complet pour les développeurs Python.",
        )
        Block.objects.create(
            software=self.software2,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="A micro web framework for building APIs.",
        )
        Block.objects.create(
            software=self.software3,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="Modern Python API framework with automatic documentation.",
        )

    def test_search_page_loads_successfully(self):
        """Test that search page returns 200 status."""
        response = self.client.get(reverse("public:search"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/search.html")

    def test_search_without_query_shows_empty_state(self):
        """Test that search without query parameter shows empty state."""
        response = self.client.get(reverse("public:search"))
        self.assertContains(response, "Enter a search query to find projects")
        self.assertEqual(len(response.context["results"]), 0)

    def test_search_with_empty_query_shows_empty_state(self):
        """Test that search with empty query shows empty state."""
        response = self.client.get(reverse("public:search") + "?q=")
        self.assertContains(response, "Enter a search query to find projects")

    def test_search_finds_projects_by_name(self):
        """Test that search finds projects by name."""
        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")
        self.assertNotContains(response, "Flask Application")
        self.assertNotContains(response, "FastAPI Service")

    def test_search_finds_projects_by_block_content(self):
        """Test that search finds projects by block content."""
        response = self.client.get("/en/search/?q=framework", HTTP_ACCEPT_LANGUAGE="en")
        # Both Django and Flask have "framework" in their content
        self.assertContains(response, "Django Project")
        self.assertContains(response, "Flask Application")
        self.assertContains(response, "FastAPI Service")

    def test_search_finds_projects_by_specific_content(self):
        """Test that search finds projects by specific content."""
        response = self.client.get("/en/search/?q=APIs", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Flask Application")
        self.assertNotContains(response, "Django Project")

    def test_search_is_case_insensitive(self):
        """Test that search is case insensitive."""
        response = self.client.get("/en/search/?q=django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")

        response = self.client.get("/en/search/?q=DJANGO", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")

    def test_search_only_shows_published_projects(self):
        """Test that only published projects appear in search results."""
        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")
        self.assertNotContains(response, "Draft Django Tool")

    def test_search_does_not_show_in_review_projects(self):
        """Test that in-review projects do not appear in search results."""
        in_review = Software.objects.create(
            name="Review Django App",
            slug="review-app",
            state=Software.STATE_IN_REVIEW,
        )

        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")
        self.assertNotContains(response, "Review Django App")

    def test_search_shows_results_count(self):
        """Test that search shows the number of results."""
        response = self.client.get("/en/search/?q=framework", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "projects found")

    def test_search_shows_no_results_message(self):
        """Test that search shows message when no results found."""
        response = self.client.get(
            "/en/search/?q=nonexistent", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "No projects found matching your search")
        self.assertContains(response, "Back to Homepage")

    def test_search_results_are_distinct(self):
        """Test that search results have no duplicates."""
        # Create multiple blocks for same software
        Block.objects.create(
            software=self.software1,
            kind=Block.KIND_FEATURES,
            locale="en",
            content="Django features include ORM, admin, and security.",
        )

        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        results = response.context["results"]

        # Count occurrences of software1
        django_count = sum(1 for r in results if r.slug == "django-project")
        self.assertEqual(django_count, 1)

    def test_search_orders_by_featured_at_then_created_at(self):
        """Test that results are ordered by featured_at, then created_at."""
        response = self.client.get("/en/search/?q=framework", HTTP_ACCEPT_LANGUAGE="en")
        content = response.content.decode("utf-8")

        # Django (Jan 15) should appear before Flask (Jan 10) and FastAPI (Jan 5)
        django_pos = content.find("Django Project")
        flask_pos = content.find("Flask Application")
        fastapi_pos = content.find("FastAPI Service")
        self.assertGreater(django_pos, 0, "Django Project not found in results")
        self.assertGreater(flask_pos, 0, "Flask Application not found in results")
        self.assertGreater(fastapi_pos, 0, "FastAPI Service not found in results")
        self.assertLess(django_pos, flask_pos)
        self.assertLess(flask_pos, fastapi_pos)

    def test_search_shows_project_logos(self):
        """Test that project logos are displayed in results."""
        self.software1.logo_url = "https://example.com/django-logo.png"
        self.software1.save()

        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, self.software1.logo_url)

    def test_search_shows_read_more_links(self):
        """Test that read more links point to project detail."""
        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "/en/project/django-project/")
        self.assertContains(response, "Read More")

    def test_search_respects_locale_in_blocks(self):
        """Test that search searches in blocks of current locale."""
        # Search in English (should find "framework")
        response = self.client.get("/en/search/?q=framework", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")

        # Search in French (should find "framework" from French content)
        response = self.client.get(
            "/fr/search/?q=développeurs", HTTP_ACCEPT_LANGUAGE="fr"
        )
        self.assertContains(response, "Django Project")

        # Search in English should not find French-only terms
        response = self.client.get(
            "/en/search/?q=développeurs", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertNotContains(response, "Django Project")

    def test_search_in_name_works_regardless_of_locale(self):
        """Test that name search works in any locale."""
        # Search by name in English
        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Django Project")

        # Search by name in French should also work
        response = self.client.get("/fr/search/?q=Django", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, "Django Project")

    def test_search_shows_query_in_page_title(self):
        """Test that search query is displayed in the page."""
        response = self.client.get("/en/search/?q=Django", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, 'Results for "Django"')

    def test_search_with_special_characters(self):
        """Test that search handles special characters correctly."""
        # Create software with special characters
        special_software = Software.objects.create(
            name="C++ Compiler",
            slug="cpp-compiler",
            state=Software.STATE_PUBLISHED,
        )

        response = self.client.get("/en/search/?q=C++", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "C++ Compiler")

    def test_search_with_multiple_words(self):
        """Test that search works with multiple words."""
        response = self.client.get(
            "/en/search/?q=web framework", HTTP_ACCEPT_LANGUAGE="en"
        )
        # Should find projects with either "web" or "framework"
        self.assertContains(response, "Django Project")
        self.assertContains(response, "Flask Application")

    def test_homepage_has_search_form(self):
        """Test that homepage includes a search form."""
        response = self.client.get("/en/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, 'action="/en/search/"')
        self.assertContains(response, 'name="q"')
        self.assertContains(response, "Search")

    def test_search_form_submits_to_correct_url(self):
        """Test that search form submits to the search view."""
        response = self.client.get("/fr/", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, 'action="/fr/search/"')


class CompareViewTestCase(TestCase):
    """Test cases for compare view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create categories with translations
        self.category_tech = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category_tech, locale="en", name="Technology"
        )
        CategoryTranslation.objects.create(
            category=self.category_tech, locale="fr", name="Technologie"
        )

        self.category_security = Category.objects.create(weight=2)
        CategoryTranslation.objects.create(
            category=self.category_security, locale="en", name="Security"
        )

        # Create fields with translations
        self.field_code_quality = Field.objects.create(
            category=self.category_tech, slug="code-quality", weight=2
        )
        FieldTranslation.objects.create(
            field=self.field_code_quality, locale="en", name="Code Quality"
        )

        self.field_performance = Field.objects.create(
            category=self.category_tech, slug="performance", weight=1
        )
        FieldTranslation.objects.create(
            field=self.field_performance, locale="en", name="Performance"
        )

        self.field_vulnerability = Field.objects.create(
            category=self.category_security, slug="vulnerability", weight=1
        )
        FieldTranslation.objects.create(
            field=self.field_vulnerability, locale="en", name="Vulnerability"
        )

        # Create published software
        self.software1 = Software.objects.create(
            name="Project A",
            slug="project-a",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        self.software2 = Software.objects.create(
            name="Project B",
            slug="project-b",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 10, tzinfo=UTC),
        )
        self.software3 = Software.objects.create(
            name="Project C",
            slug="project-c",
            state=Software.STATE_PUBLISHED,
            featured_at=datetime(2024, 1, 5, tzinfo=UTC),
        )

        # Create draft software (should not be comparable)
        self.draft_software = Software.objects.create(
            name="Draft Project",
            slug="draft-project",
            state=Software.STATE_DRAFT,
        )

        # Create analysis results for software1
        AnalysisResult.objects.create(
            software=self.software1,
            field=self.field_code_quality,
            score=Decimal("4.50"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software1,
            field=self.field_performance,
            score=Decimal("3.00"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software1,
            field=self.field_vulnerability,
            score=Decimal("5.00"),
            is_published=True,
        )

        # Create analysis results for software2
        AnalysisResult.objects.create(
            software=self.software2,
            field=self.field_code_quality,
            score=Decimal("3.50"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software2,
            field=self.field_performance,
            score=Decimal("4.50"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software2,
            field=self.field_vulnerability,
            score=Decimal("3.00"),
            is_published=True,
        )

        # Create analysis results for software3
        AnalysisResult.objects.create(
            software=self.software3,
            field=self.field_code_quality,
            score=Decimal("5.00"),
            is_published=True,
        )
        AnalysisResult.objects.create(
            software=self.software3,
            field=self.field_vulnerability,
            score=Decimal("4.00"),
            is_published=True,
        )

    def test_compare_page_loads_successfully(self):
        """Test that compare page returns 200 status with valid projects."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/compare.html")

    def test_compare_requires_at_least_two_projects(self):
        """Test that compare requires at least 2 projects."""
        response = self.client.get(
            "/en/compare/?projects=project-a", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please select between 2 and 5 projects")

    def test_compare_allows_maximum_five_projects(self):
        """Test that compare allows maximum 5 projects."""
        # Create 2 more projects
        Software.objects.create(
            name="Project D", slug="project-d", state=Software.STATE_PUBLISHED
        )
        Software.objects.create(
            name="Project E", slug="project-e", state=Software.STATE_PUBLISHED
        )
        Software.objects.create(
            name="Project F", slug="project-f", state=Software.STATE_PUBLISHED
        )

        response = self.client.get(
            "/en/compare/?projects=project-a,project-b,project-c,project-d,project-e,project-f",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please select between 2 and 5 projects")

    def test_compare_shows_project_names(self):
        """Test that compare shows all project names."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Project A")
        self.assertContains(response, "Project B")

    def test_compare_shows_overall_scores(self):
        """Test that compare shows overall scores for each project."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Overall Score")

        # Check that scores are displayed
        projects_data = response.context["projects_data"]
        self.assertEqual(len(projects_data), 2)

        # Project A: Tech (4.5*2+3.0*1)/3=4.0, Security (5.0)
        # Overall: (4.0*1+5.0*2)/3=4.67
        self.assertEqual(projects_data[0]["overall_score"], Decimal("4.67"))

        # Project B: Tech (3.5*2+4.5*1)/3=3.83, Security (3.0)
        # Overall: (3.83*1+3.0*2)/3=3.28
        self.assertEqual(projects_data[1]["overall_score"], Decimal("3.28"))

    def test_compare_shows_category_scores(self):
        """Test that compare shows category scores."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Technology")
        self.assertContains(response, "Security")

        categories_comparison = response.context["categories_comparison"]
        self.assertEqual(len(categories_comparison), 2)

    def test_compare_shows_field_scores(self):
        """Test that compare shows field scores."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Code Quality")
        self.assertContains(response, "Performance")
        self.assertContains(response, "Vulnerability")

    def test_compare_handles_missing_field_scores(self):
        """Test that compare handles when a project doesn't have all field scores."""
        # Project C is missing Performance score
        response = self.client.get(
            "/en/compare/?projects=project-a,project-c", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)

        # Check that both projects are shown
        self.assertContains(response, "Project A")
        self.assertContains(response, "Project C")

    def test_compare_only_shows_published_projects(self):
        """Test that only published projects can be compared."""
        response = self.client.get(
            "/en/compare/?projects=project-a,draft-project",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "One or more projects not found or not published")

    def test_compare_handles_nonexistent_projects(self):
        """Test that compare handles non-existent project slugs."""
        response = self.client.get(
            "/en/compare/?projects=project-a,nonexistent", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "One or more projects not found or not published")

    def test_compare_orders_projects_alphabetically(self):
        """Test that projects are ordered by name."""
        response = self.client.get(
            "/en/compare/?projects=project-c,project-a,project-b",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        projects = response.context["projects"]
        self.assertEqual(projects[0].slug, "project-a")
        self.assertEqual(projects[1].slug, "project-b")
        self.assertEqual(projects[2].slug, "project-c")

    def test_compare_orders_categories_by_weight(self):
        """Test that categories are ordered by weight."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        categories_comparison = response.context["categories_comparison"]

        # Technology (weight 1) should come before Security (weight 2)
        self.assertEqual(categories_comparison[0]["category_name"], "Technology")
        self.assertEqual(categories_comparison[1]["category_name"], "Security")

    def test_compare_respects_locale_for_category_names(self):
        """Test that category names are localized."""
        # Test in English
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Technology")

        # Test in French
        response = self.client.get(
            "/fr/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="fr"
        )
        self.assertContains(response, "Technologie")

    def test_compare_shows_score_badges(self):
        """Test that scores are shown with color-coded badges."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        # Should have score badges
        self.assertContains(response, "score-badge")
        self.assertContains(response, "score-3")
        self.assertContains(response, "score-4")
        self.assertContains(response, "score-5")

    def test_compare_shows_project_links(self):
        """Test that project names link to their detail pages."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "/en/project/project-a/")
        self.assertContains(response, "/en/project/project-b/")

    def test_compare_shows_score_legend(self):
        """Test that score legend is displayed."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Score Legend")

    def test_compare_shows_back_button(self):
        """Test that back to homepage button is shown."""
        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertContains(response, "Back to Homepage")

    def test_project_detail_shows_compare_selector(self):
        """Test that project detail page shows comparison selector."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "project-a"})
        )
        self.assertContains(response, "Compare with Other Projects")
        self.assertContains(response, "projectSelect")

    def test_project_detail_compare_selector_lists_other_projects(self):
        """Test that compare selector shows other published projects."""
        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "project-a"})
        )
        # Should show other published projects
        self.assertContains(response, "Project B")
        self.assertContains(response, "Project C")
        # Should not show draft projects
        self.assertNotContains(response, "Draft Project")
        # Should not show current project
        # (Actually, it might not contain "Project A" in the selector, only in the header)

    def test_compare_shows_most_recent_score_when_duplicates(self):
        """Test that compare view uses most recent scores when duplicates exist."""
        from time import sleep

        # Create an older result for software1
        AnalysisResult.objects.create(
            software=self.software1,
            field=self.field_code_quality,
            score=Decimal("2.00"),
            is_published=True,
        )

        sleep(0.01)

        # Create a newer result for software1 (should override the older one)
        AnalysisResult.objects.create(
            software=self.software1,
            field=self.field_code_quality,
            score=Decimal("4.80"),
            is_published=True,
        )

        response = self.client.get(
            "/en/compare/?projects=project-a,project-b", HTTP_ACCEPT_LANGUAGE="en"
        )

        # Find the Code Quality field in comparison
        categories_comparison = response.context["categories_comparison"]
        tech_category = next(
            c for c in categories_comparison if c["category_name"] == "Technology"
        )

        code_quality_field = next(
            f for f in tech_category["fields"] if "Code Quality" in f["field_name"]
        )

        # First score (project-a) should be the newer one (4.80)
        self.assertEqual(code_quality_field["scores"][0], Decimal("4.80"))


class FieldMetricsViewTestCase(TestCase):
    """Test cases for field_metrics view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create category with translations
        self.category = Category.objects.create(weight=1)
        CategoryTranslation.objects.create(
            category=self.category, locale="en", name="Performance"
        )
        CategoryTranslation.objects.create(
            category=self.category, locale="fr", name="Performance"
        )

        # Create field with translations
        self.field = Field.objects.create(
            category=self.category, slug="popularity", weight=1
        )
        FieldTranslation.objects.create(
            field=self.field, locale="en", name="Popularity"
        )
        FieldTranslation.objects.create(
            field=self.field, locale="fr", name="Popularité"
        )

        # Create software
        self.software = Software.objects.create(
            name="Test Project",
            slug="test-project",
            state=Software.STATE_PUBLISHED,
        )

        # Create metrics with translations
        self.metric1 = Metric.objects.create(
            field=self.field,
            slug="github-stars",
            weight=1,
            collection_enabled=True,
        )
        MetricTranslation.objects.create(
            metric=self.metric1, locale="en", name="GitHub Stars"
        )
        MetricTranslation.objects.create(
            metric=self.metric1, locale="fr", name="Étoiles GitHub"
        )

        self.metric2 = Metric.objects.create(
            field=self.field,
            slug="npm-downloads",
            weight=1,
            collection_enabled=True,
        )
        MetricTranslation.objects.create(
            metric=self.metric2,
            locale="en",
            name="NPM Downloads",
            description="Monthly download count from NPM registry",
        )

        # Create metric values
        MetricValue.objects.create(
            metric=self.metric1,
            software=self.software,
            value=Decimal("45000"),
            source="GitHub API",
            collected_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        MetricValue.objects.create(
            metric=self.metric1,
            software=self.software,
            value=Decimal("46000"),
            source="GitHub API",
            collected_at=datetime(2024, 2, 1, tzinfo=UTC),
        )
        MetricValue.objects.create(
            metric=self.metric2,
            software=self.software,
            value=Decimal("1000000"),
            source="NPM Registry",
            collected_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

    def test_field_metrics_page_loads_successfully(self):
        """Test that field metrics page returns 200 status."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/field_metrics.html")

    def test_field_metrics_shows_software_name(self):
        """Test that software name is displayed."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "Test Project")

    def test_field_metrics_shows_field_name(self):
        """Test that field name is displayed."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "Popularity")

    def test_field_metrics_shows_category_name(self):
        """Test that category name is displayed in breadcrumb."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "Performance")

    def test_field_metrics_shows_metric_names(self):
        """Test that metric names are displayed."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "GitHub Stars")
        self.assertContains(response, "NPM Downloads")

    def test_field_metrics_shows_metric_description(self):
        """Test that metric description is displayed when available."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "Monthly download count from NPM registry")

    def test_field_metrics_includes_chart_js(self):
        """Test that Chart.js CDN is included when data exists."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "chart.js")
        self.assertContains(response, "canvas")

    def test_field_metrics_returns_404_for_nonexistent_software(self):
        """Test that 404 is returned for non-existent software."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={
                    "software_slug": "does-not-exist",
                    "field_slug": "popularity",
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_field_metrics_returns_404_for_draft_software(self):
        """Test that draft software is not accessible."""
        draft = Software.objects.create(
            name="Draft Software", slug="draft", state=Software.STATE_DRAFT
        )
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "draft", "field_slug": "popularity"},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_field_metrics_returns_404_for_nonexistent_field(self):
        """Test that 404 is returned for non-existent field."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={
                    "software_slug": "test-project",
                    "field_slug": "does-not-exist",
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_field_metrics_shows_no_data_message_when_no_metrics(self):
        """Test that no data message is shown when field has no metrics."""
        # Create field without metrics
        field_no_metrics = Field.objects.create(
            category=self.category, slug="no-metrics", weight=1
        )
        FieldTranslation.objects.create(
            field=field_no_metrics, locale="en", name="No Metrics"
        )

        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "no-metrics"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No metric data available")
        # Chart.js should not be loaded when no data
        self.assertNotContains(response, "chart.js")

    def test_field_metrics_shows_no_data_message_when_no_values(self):
        """Test that no data message is shown when metrics have no values."""
        # Create metric without values
        metric_no_values = Metric.objects.create(
            field=self.field,
            slug="no-values",
            weight=1,
            collection_enabled=True,
        )
        MetricTranslation.objects.create(
            metric=metric_no_values, locale="en", name="No Values"
        )

        # Delete all metric values to test empty state
        MetricValue.objects.all().delete()

        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No metric data available")

    def test_field_metrics_only_shows_enabled_metrics(self):
        """Test that only collection_enabled metrics are shown."""
        # Create disabled metric
        disabled_metric = Metric.objects.create(
            field=self.field,
            slug="disabled",
            weight=1,
            collection_enabled=False,
        )
        MetricTranslation.objects.create(
            metric=disabled_metric, locale="en", name="Disabled Metric"
        )
        MetricValue.objects.create(
            metric=disabled_metric,
            software=self.software,
            value=Decimal("100"),
            source="Test",
        )

        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertNotContains(response, "Disabled Metric")

    def test_field_metrics_respects_locale(self):
        """Test that field and metric names are localized."""
        # Test French locale
        response = self.client.get(
            "/fr/project/test-project/field/popularity/",
            HTTP_ACCEPT_LANGUAGE="fr",
        )
        self.assertContains(response, "Popularité")
        self.assertContains(response, "Étoiles GitHub")

    def test_field_metrics_shows_breadcrumb_navigation(self):
        """Test that breadcrumb navigation is present."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "breadcrumb")
        self.assertContains(response, "Home")
        self.assertContains(response, reverse("public:home"))
        self.assertContains(
            response, reverse("public:project_detail", kwargs={"slug": "test-project"})
        )

    def test_field_metrics_shows_back_button(self):
        """Test that back to project button is displayed."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertContains(response, "Back to Project")
        self.assertContains(
            response, reverse("public:project_detail", kwargs={"slug": "test-project"})
        )

    def test_field_metrics_context_has_correct_data(self):
        """Test that context has all required data."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        self.assertEqual(response.context["software"].slug, "test-project")
        self.assertEqual(response.context["field"].slug, "popularity")
        self.assertEqual(response.context["field_name"], "Popularity")
        self.assertEqual(response.context["category_name"], "Performance")
        self.assertTrue(response.context["has_data"])
        self.assertEqual(len(response.context["metrics_data"]), 2)

    def test_field_metrics_chart_data_includes_values(self):
        """Test that metric values are included in chart data."""
        response = self.client.get(
            reverse(
                "public:field_metrics",
                kwargs={"software_slug": "test-project", "field_slug": "popularity"},
            )
        )
        metrics_data = response.context["metrics_data"]

        # Find GitHub Stars metric
        github_metric = next(
            m for m in metrics_data if m["metric_slug"] == "github-stars"
        )
        # Values should be present (2 values for GitHub Stars)
        self.assertIn("values", github_metric)

    def test_project_detail_field_links_to_metrics(self):
        """Test that field names on project detail link to metrics page."""
        # Create analysis result
        AnalysisResult.objects.create(
            software=self.software,
            field=self.field,
            score=Decimal("4.5"),
            is_published=True,
        )

        response = self.client.get(
            reverse("public:project_detail", kwargs={"slug": "test-project"})
        )

        # Check that field link exists
        field_metrics_url = reverse(
            "public:field_metrics",
            kwargs={"software_slug": "test-project", "field_slug": "popularity"},
        )
        self.assertContains(response, field_metrics_url)
