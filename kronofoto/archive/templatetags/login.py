from django import template
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login

register = template.Library()

@register.inclusion_tag('archive/login.html', takes_context=True)
def make_login(context):
    request = context['request']
    form = AuthenticationForm(request)
    return { 'form': form, 'user': request.user, 'request': request}
