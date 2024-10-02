from django import template
from django.apps import apps

if not apps.is_installed("cms"):
    register = template.Library()
    @register.simple_tag
    def show_menu_below_id(*args):
        pass
