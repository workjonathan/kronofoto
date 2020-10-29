from django import template
from ..forms import SearchForm

register = template.Library()

@register.inclusion_tag('archive/search_form.html', takes_context=True)
def make_search_form(context):
    params = None
    if 'search-form' in context:
        form = context['search-form']
        params = context['request'].GET
    else:
        form = SearchForm()
    return { 'form': form, 'vary_on': params }
