from django import template

register = template.Library()

@register.inclusion_tag('archive/timeline.svg')
def make_timeline(years):
    years = [(lbl, href, i*3+1) for (i,(lbl, href)) in enumerate(years)]
    return {
        'years': years,
        'viewBox': [0, 0, len(years)*3, 10],

    }
