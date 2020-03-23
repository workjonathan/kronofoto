from django import template

register = template.Library()

@register.inclusion_tag('archive/photodetail.html')
def show_photo(photo):
    return {'photo': photo }
