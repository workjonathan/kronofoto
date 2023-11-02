from django.http import HttpRequest
from typing import Dict, Any, Optional
from django.conf import settings
import random
from .views.basetemplate import THEME # type: ignore
from django.urls import resolve
from django.core.cache import cache
import json
from .models import Photo

def kronofoto_context(request: HttpRequest, short_name: Optional[str]=None) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    if 'kronofoto' in resolve(request.path_info).app_names:
        hxheaders = dict()
        hxheaders['Constraint'] = request.headers.get('Constraint', None)
        hxheaders['Embedded'] = request.headers.get('Embedded', 'false')
        context['hxheaders'] = json.dumps(hxheaders)
        context['KF_DJANGOCMS_NAVIGATION'] = settings.KF_DJANGOCMS_NAVIGATION
        context['KF_DJANGOCMS_ROOT'] = settings.KF_DJANGOCMS_ROOT
    context['theme'] = random.choice(THEME[short_name if short_name else 'us'])
    return context
