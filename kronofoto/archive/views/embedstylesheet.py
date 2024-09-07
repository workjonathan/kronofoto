from django.views.generic import TemplateView
from typing import Any, Dict


class EmbedStyleSheet(TemplateView):
    template_name = 'archive/id.css'
    content_type = 'text/css'

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context['id'] = self.kwargs['id']
        return context
