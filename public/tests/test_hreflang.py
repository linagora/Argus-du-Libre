from django.test import RequestFactory, TestCase
from django.template import RequestContext, Template

from public.templatetags import hreflang as hreflang_tag
from public.templatetags.hreflang import get_locale_alternates


class HreflangTagTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_builds_locale_alternates_with_query(self):
        request = self.factory.get("/en/project/?q=42", HTTP_HOST="example.com")
        alternates = get_locale_alternates(request)
        en = next(a for a in alternates if a["locale"] == "en")
        fr = next(a for a in alternates if a["locale"] == "fr")
        x_default = next(a for a in alternates if a["locale"] == "x-default")

        self.assertTrue(en["url"].endswith("/en/project/?q=42"))
        self.assertIn("?q=42", fr["url"])
        self.assertEqual(x_default["url"], en["url"])

    def test_unprefixed_path_yields_documented_locales(self):
        request = self.factory.get("/project/?size=1", HTTP_HOST="example.com")
        alternates = get_locale_alternates(request)
        locales = {alt["locale"] for alt in alternates}
        self.assertEqual(locales, set(hreflang_tag.SUPPORTED_LOCALES) | {"x-default"})

    def test_returns_empty_list_when_request_missing(self):
        self.assertEqual(get_locale_alternates(None), [])

    def test_supported_locales_override_limits_output(self):
        original = hreflang_tag.SUPPORTED_LOCALES
        hreflang_tag.SUPPORTED_LOCALES = ("en",)
        try:
            request = self.factory.get("/en/project/", HTTP_HOST="example.com")
            alternates = get_locale_alternates(request)
            locales = {alt["locale"] for alt in alternates}
            self.assertEqual(locales, {"en", "x-default"})
        finally:
            hreflang_tag.SUPPORTED_LOCALES = original

    def test_template_outputs_hreflang_links_with_query(self):
        request = self.factory.get("/en/home/?q=abc", HTTP_HOST="example.com")
        tpl = Template(
            "{% load hreflang %}{% get_locale_alternates request as hreflang_tags %}"
            '{% for alt in hreflang_tags %}<link rel="alternate" href="{{ alt.url }}" hreflang="{{ alt.locale }}" data-test>{{ alt.locale }}</link>{% endfor %}'
        )
        rendered = tpl.render(RequestContext(request))

        self.assertIn('hreflang="en"', rendered)
        self.assertIn('hreflang="fr"', rendered)
        self.assertIn('hreflang="x-default"', rendered)
        self.assertIn("?q=abc", rendered)
