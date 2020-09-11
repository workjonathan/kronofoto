from django import template
from ..forms import SearchForm

register = template.Library()

@register.inclusion_tag('archive/doc-nav.html', takes_context=False)
def docnav(active_item=None):
    # These are pairs of display text and view names.
    pages = (
        ('Home', 'random-image'),
        ('About', 'about'),
        ('Use', 'use'),
        ('Contribute', 'contribute'),
        ('Volunteer', 'volunteer'),
    )
    return {
        'pages': [
            {
                'text': text,
                'view_name': view_name,
                'is_active': active_item == text
            }
            for text, view_name in pages
        ],
    }
