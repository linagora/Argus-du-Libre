"""Helpers for building SEO-friendly meta descriptions."""

import re

from django.utils.html import strip_tags

MAX_META_DESCRIPTION_LENGTH = 160
_MARKDOWN_CLEANUP = re.compile(r"[*_\[\]`#>]+")


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    text = strip_tags(value)
    text = _MARKDOWN_CLEANUP.sub(" ", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.strip()


def clean_description(
    raw_text: str,
    fallback: str | None = None,
    max_length: int = MAX_META_DESCRIPTION_LENGTH,
) -> str | None:
    """Return a normalized, truncated description or the fallback if empty."""

    text = _normalize_text(raw_text)
    if not text:
        return fallback
    return _truncate(text, max_length)
