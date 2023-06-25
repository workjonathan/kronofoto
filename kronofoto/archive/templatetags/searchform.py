from django import template
from ..forms import SearchForm, TimelineForm

register = template.Library()

@register.inclusion_tag('archive/search_form.html', takes_context=True)
def make_search_form(context):
    params = None
    if 'search-form' in context:
        form = context['search-form']
        params = context['request'].GET
    else:
        form = SearchForm()
    return { 'form': form, 'vary_on': params, 'theme': context['theme'], 'url_kwargs': context['url_kwargs'], 'get_params': context['get_params']}

@register.inclusion_tag("archive/timeline.html", takes_context=True)
def timeline(context):
    return {
        'form': TimelineForm(context['request'].GET, auto_id="timeline_id_%s"),
        'object': context['object'],
        'queryset': context['queryset'],
    }
