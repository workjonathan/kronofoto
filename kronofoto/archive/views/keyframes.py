from django.views.generic import TemplateView
from typing import Any, Dict


class Keyframes(TemplateView):
    template_name = "archive/keyframes.css"
    content_type = 'text/css'
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        origin = self.kwargs['origin']
        difference = self.kwargs['difference']
        step = self.kwargs['step']
        unit = self.kwargs['unit']
        animations = []
        for i in range(0, difference, step):
            animations.append({'from': origin-i, 'to': origin-difference})
            animations.append({'from': origin+i, 'to': origin+difference})
        context['keyframes'] = animations
        context['unit'] = unit
        return context


