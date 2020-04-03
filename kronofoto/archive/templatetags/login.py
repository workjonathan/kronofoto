from django import template
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login

register = template.Library()

@register.inclusion_tag('registration/login.html', takes_context=True)
def make_login(context):
    request = context['request']
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, form.get_user())
    else:
        form = AuthenticationForm(request)
    return { 'form': form, 'user': request.user, 'request': request}
