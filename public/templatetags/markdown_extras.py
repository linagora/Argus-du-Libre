"""Markdown template filters."""

import markdown
from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_format(text):
    """Convert markdown text to HTML."""
    if not text:
        return ""
    return mark_safe(markdown.markdown(text, extensions=["fenced_code", "tables"]))


@register.filter(name="strip_markdown")
def strip_markdown(text):
    """Convert markdown to plain text by rendering and stripping HTML."""
    if not text:
        return ""
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])
    return strip_tags(html)
