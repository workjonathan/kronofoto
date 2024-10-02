from django import template
from fortepan_us.kronofoto.forms import SearchForm, TimelineForm, CarouselForm

register = template.Library()

@register.inclusion_tag('kronofoto/components/make_search_form.html', takes_context=True)
def make_search_form(context):
    params = None
    if 'search-form' in context:
        form = context['search-form']
        params = context['request'].GET
    else:
        form = SearchForm()
    return { 'form': form, 'vary_on': params, 'theme': context['theme'], 'url_kwargs': context['url_kwargs'], 'get_params': context['get_params']}

@register.inclusion_tag("kronofoto/components/timeline.html", takes_context=True)
def timeline(context):
    return {
        'form': TimelineForm(context['request'].GET, auto_id="timeline_id_%s"),
        'object': context['object'],
        'queryset': context['queryset'],
    }

@register.inclusion_tag("kronofoto/components/carousel_form.html", takes_context=True)
def carousel_form(context):
    object = context['object']
    initial = context['request'].GET.copy()
    initial['id'] = object.id
    initial['forward'] = True
    return {
        'form': CarouselForm(initial=initial, auto_id="carousel_id_%s"),
    }
