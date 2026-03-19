"""Django sitemap definitions for the public app."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from projects.models import Software, Tag


class SoftwareSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Software.objects.filter(state=Software.STATE_PUBLISHED).order_by("slug")

    def lastmod(self, obj: Software):
        return obj.updated_at

    def location(self, obj: Software):
        return reverse("public:project_detail", args=[obj.slug])


class TagSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Tag.objects.filter(softwares__state=Software.STATE_PUBLISHED).distinct()

    def location(self, obj: Tag):
        return reverse("public:tag_detail", args=[obj.slug])

    def lastmod(self, obj: Tag):
        opinion = obj.opinions.order_by("-updated_at").first()
        return opinion.updated_at if opinion else None


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return [
            "public:home",
            "public:tags_list",
            "public:scores_help",
            "public:about",
        ]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "projects": SoftwareSitemap(),
    "tags": TagSitemap(),
    "static": StaticViewSitemap(),
}
