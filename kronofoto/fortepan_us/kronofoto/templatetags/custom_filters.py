from django import template
import re
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='strip_p_tags')
def strip_p_tags(value):
    """Removes <p> and </p> tags from a given text."""
    cleaned_text = re.sub(r"</?p>", "", value, flags=re.IGNORECASE)
    return mark_safe(cleaned_text)
