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
        self.assertRegex(content, r'score-badge score-\d+')

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
        self.assertNotContains(response, 'Overall Score:</span>')

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
        response = self.client.get(
            "/en/tag/database/", HTTP_ACCEPT_LANGUAGE="en"
        )
        project_url = "/en/project/software-1/"
        self.assertContains(response, project_url)
        self.assertContains(response, "Read More")

    def test_tag_detail_empty_state(self):
        """Test that empty state is shown when no projects have the tag."""
        tag_no_projects = Tag.objects.create(name="Empty Tag", slug="empty-tag")

        response = self.client.get(
            "/en/tag/empty-tag/", HTTP_ACCEPT_LANGUAGE="en"
        )
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
