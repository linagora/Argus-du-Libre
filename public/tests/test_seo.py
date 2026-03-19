from django.test import TestCase
from django.urls import reverse

from projects.models import Block, Software, Tag, TagOpinion


class SeoMetaDescriptionTests(TestCase):
    def setUp(self):
        self.software = Software.objects.create(
            name="ArgusTest",
            slug="argus-test",
            state=Software.STATE_PUBLISHED,
        )
        Block.objects.create(
            software=self.software,
            kind=Block.KIND_OVERVIEW,
            locale="en",
            content="Overview with **bold** description.",
        )

        self.tag = Tag.objects.create(name="Collaboration", slug="collaboration")
        self.tag.softwares.add(self.software)
        TagOpinion.objects.create(
            tag=self.tag,
            locale="en",
            content="Opinionated summary for collaboration.",
        )

    def test_project_detail_sets_description(self):
        response = self.client.get(
            reverse("public:project_detail", args=[self.software.slug])
        )
        description = response.context.get("meta_description")
        self.assertIsInstance(description, str)
        self.assertIn("Overview with bold description.", description)

    def test_tag_detail_sets_description(self):
        response = self.client.get(reverse("public:tag_detail", args=[self.tag.slug]))
        description = response.context.get("meta_description")
        self.assertIsInstance(description, str)
        self.assertIn("Opinionated summary", description)

    def test_search_sets_description_for_query(self):
        response = self.client.get(reverse("public:search"), {"q": "collaboration"})
        description = response.context.get("meta_description")
        self.assertIsInstance(description, str)
        self.assertIn("collaboration", description.lower())
