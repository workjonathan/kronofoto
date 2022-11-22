from django import template
from ..forms import SearchForm

register = template.Library()

@register.inclusion_tag('archive/doc-nav.html', takes_context=True)
def docnav(context, active_item=None):
    # These are pairs of display text and view names.
    pages = (
        #('Archive', 'random-image'),
        ('About', 'about'),
        ('Use', 'use'),
        ('Contribute', 'contribute'),
        ('Volunteer', 'volunteer'),
        ('Give', 'give'),
    )
    context['pages'] = [
        {
            'text': text,
            'view_name': view_name,
            'is_active': active_item == text
        }
        for text, view_name in pages
    ]
    return context
