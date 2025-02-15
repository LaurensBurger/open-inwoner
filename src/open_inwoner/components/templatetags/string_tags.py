from django import template
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html

register = template.Library()


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)


@register.simple_tag
def optional_paragraph(optional_text: str) -> str:
    """
    Renders the provided optional text, if it exists, or an empty string.

    Usage:
        {% optional_paragraph optional_text %}

    Variables:
        + optional_text: string | This is the optional text.
    """
    if not optional_text:
        return ""
    return format_html(
        '<p class="p">{optional_text}</p>'.format(
            optional_text=linebreaksbr(optional_text)
        )
    )
