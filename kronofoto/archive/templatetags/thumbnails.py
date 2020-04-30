from django import template

register = template.Library()

@register.inclusion_tag('archive/thumbnails.html')
def make_thumbnails(this_page, prev_page, next_page, getparams):
    context = {
        'page': this_page,
        'prev_page': prev_page,
        'next_page': next_page,
        'getparams': getparams,
    }
    return context
