from django import template
from ..forms import SearchForm

register = template.Library()

@register.inclusion_tag('archive/search_form.html', takes_context=True)
def make_search_form(context):
    form = context['search-form'] if 'search-form' in context else SearchForm()
    return { 'form': form }
