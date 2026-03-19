from django.test import TestCase
from django.urls import reverse

from projects.models import Software, Tag


class SitemapTests(TestCase):
    def setUp(self):
        self.software = Software.objects.create(
            name="ArgusMap",
            slug="argus-map",
            state=Software.STATE_PUBLISHED,
        )
        self.tag = Tag.objects.create(name="Mapping", slug="mapping")
        self.tag.softwares.add(self.software)

    def test_sitemap_contains_project_and_static_url(self):
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        project_url = reverse("public:project_detail", args=[self.software.slug])
        self.assertIn(project_url, content)
        self.assertIn(reverse("public:home"), content)
