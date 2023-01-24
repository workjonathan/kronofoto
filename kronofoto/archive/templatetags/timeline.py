from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag('archive/timeline.svg')
def make_timeline(start, end, request, width=400):
    context = {
        'minornotches': [],
        'majornotches': [],
        'viewBox': [0, 0, width, 10],
    }
    years = end-start+1
    for i, year in enumerate(range(start, end+1)):
        xpos = i*width/years
        boxwidth = width/years
        marker = {
            'target': "{}?{}".format(reverse('year-redirect', kwargs=dict(year=year)), request.GET.urlencode()),
            'data_year': str(year),
            'box': {
                'x': xpos,
                'width': boxwidth,
                'y': 5,
                'height': 5,
            },
            'notch': {
                'x': xpos,
                'width': boxwidth/5,
                'y': 7,
                'height': 3,
            }
        }
        if year % 5 == 0:
            marker['notch']['height'] = 5
            marker['notch']['y'] = 5
        if year % 10 == 0:
            marker['notch']['height'] = 5
            marker['notch']['y'] = 5
            marker['label'] = {
                'text': str(year),
                'y': 3,
                'x': xpos + boxwidth/2,
            }
            context['majornotches'].append(marker)
        else:
            context['minornotches'].append(marker)
    return context
