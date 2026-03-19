from typing import Iterable

from django import template

register = template.Library()

SUPPORTED_LOCALES = ("en", "fr")


def _strip_locale(path_info: str) -> str:
    if not path_info:
        return "/"
    for locale in SUPPORTED_LOCALES:
        prefix = f"/{locale}"
        if path_info == prefix:
            return "/"
        if path_info.startswith(f"{prefix}/"):
            return path_info[len(prefix) :]
    return path_info


def _build_url(request, locale: str, base_path: str, query: str | None) -> str:
    target = f"/{locale}{base_path}"
    if query:
        target = f"{target}?{query}"
    return request.build_absolute_uri(target)


@register.simple_tag
def get_locale_alternates(request) -> list[dict[str, str]]:
    if not request:
        return []
    full_path = request.get_full_path()
    path_only, _, query = full_path.partition("?")
    base_path = _strip_locale(path_only)
    alternates: list[dict[str, str]] = [
        {"locale": locale, "url": _build_url(request, locale, base_path, query)}
        for locale in SUPPORTED_LOCALES
    ]
    alternates.append(
        {"locale": "x-default", "url": _build_url(request, "en", base_path, query)}
    )
    return alternates
