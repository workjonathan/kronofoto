from django.views.generic import TemplateView


class EmbedStyleSheet(TemplateView):
    template_name = 'archive/id.css'
    content_type = 'text/css'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['id'] = self.kwargs['id']
        return context
