from django import template

register = template.Library()

@register.inclusion_tag('archive/timeline.svg')
def make_timeline(years, width=400):
    context = {
        'minornotches': [],
        'majornotches': [],
        'viewBox': [0, 0, width, 10],
    }
    for (i, (year, href, json_href)) in enumerate(years):
        xpos = i*width/len(years)
        boxwidth = width/len(years)
        marker = {
            'target': href,
            'json_target': json_href,
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
