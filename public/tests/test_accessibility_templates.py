from types import SimpleNamespace

from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse


class BaseAccessibilityTest(TestCase):
    def test_base_includes_skip_link_and_nav_labels(self):
        response = self.client.get(reverse("public:home"))
        html = response.content.decode()
        self.assertIn('id="content"', html)
        self.assertIn('aria-label="Primary navigation"', html)
        self.assertIn('href="#content"', html)
        self.assertIn('aria-labelledby="page-title"', html)
        self.assertIn('id="page-title"', html)


class ComponentAccessibilityTest(TestCase):
    def render_project_card(self):
        template = Template(
            "{% include 'public/_project_card.html' with project=project score=score overview=overview %}"
        )
        project = SimpleNamespace(
            slug="test-project", name="Test Project", logo_url=None
        )
        return template.render(
            Context(
                {
                    "project": project,
                    "score": 4.2,
                    "overview": "An accessible overview.",
                }
            )
        )

    def test_project_card_has_role_and_aria_labels(self):
        html = self.render_project_card()
        self.assertIn('role="group"', html)
        self.assertIn('aria-label="Score: ', html)
        self.assertIn('aria-label="Read more about', html)

    def test_search_form_has_labels(self):
        response = self.client.get(reverse("public:home"))
        html = response.content.decode()
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-label="Refine your search"', html)
        self.assertIn('id="search-input"', html)
        self.assertIn('for="search-input"', html)
