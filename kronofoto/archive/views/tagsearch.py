from django.views.generic.list import BaseListView
from .jsonresponse import JSONResponseMixin
from ..models.tag import Tag


class TagSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self):
        return Tag.objects.filter(
            tag__icontains=self.request.GET['term'], phototag__accepted=True
        ).values('tag', 'id').distinct()[:10]

    def get_data(self, context):
        return [
            dict(id=tag['id'], value=tag['tag'], label=tag['tag'])
            for tag in context['object_list']
        ]

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, safe=False, **kwargs)
