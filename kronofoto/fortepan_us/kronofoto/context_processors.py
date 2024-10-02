from django.http import HttpRequest
from typing import Dict, Any, Optional
from django.conf import settings
import random
from fortepan_us.kronofoto.views.basetemplate import Theme
from django.urls import resolve
from django.core.cache import cache
import json
from fortepan_us.kronofoto.models import Photo, Archive

def kronofoto_context(request: HttpRequest, short_name: Optional[str]=None) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    if 'kronofoto' in resolve(request.path_info).app_names:
        short_name = resolve(request.path_info).kwargs.get('short_name') # theme should go in base.py.
        hxheaders = dict()
        context['cms_root'] = settings.KF_DJANGOCMS_ROOT
        try:
            archive = Archive.objects.get(slug=short_name)
            context['cms_root'] = archive.cms_root
        except Archive.DoesNotExist:
            pass
        hxheaders['Constraint'] = request.headers.get('Constraint', None)
        hxheaders['Embedded'] = request.headers.get('Embedded', 'false')
        context['hxheaders'] = json.dumps(hxheaders)
        context['KF_DJANGOCMS_NAVIGATION'] = settings.KF_DJANGOCMS_NAVIGATION
        context['KF_DJANGOCMS_ROOT'] = settings.KF_DJANGOCMS_ROOT
    context['theme'] = Theme.select_random_theme(short_name)
    context['CSS_VERSION'] = settings.CSS_VERSION
    return context
