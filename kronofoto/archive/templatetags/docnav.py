from django import template
from ..forms import SearchForm

register = template.Library()

@register.inclusion_tag('archive/doc-nav.html', takes_context=False)
def docnav(title=None):
    pages = (
        ('About', 'about'),
        ('Use', 'use'),
        ('Contribute', 'contribute'),
        ('Volunteer', 'volunteer'),
    )
    return {'pages': pages, 'title': title}
