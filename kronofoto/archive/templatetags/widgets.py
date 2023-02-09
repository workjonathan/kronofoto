from django import template
from .. import reverse
import markdown as md
from .urlify import URLifyExtension
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape


register = template.Library()

@register.inclusion_tag('archive/page-links.html', takes_context=False)
def page_links(formatter, page_obj, target=None):
    links = [{'label': label} for label in ['First', 'Previous', 'Next', 'Last']]
    if page_obj.has_previous():
        links[0]['url'] = formatter.page_url(1)
        links[0]['target'] = target
        links[1]['url'] = formatter.page_url(page_obj.previous_page_number())
        links[1]['target'] = target
    if page_obj.has_next():
        links[2]['url'] = formatter.page_url(page_obj.next_page_number())
        links[2]['target'] = target
        links[3]['url'] = formatter.page_url(page_obj.paginator.num_pages)
        links[3]['target'] = target
    return dict(
        links=links,
        page_obj=page_obj
    )

@register.filter(is_safe=True)
@stringfilter
def markdown(text):
    return mark_safe(md.markdown(escape(text), extensions=[URLifyExtension()]))
