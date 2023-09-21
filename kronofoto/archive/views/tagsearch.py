from django.views.generic.list import BaseListView
from .jsonresponse import JSONResponseMixin
from ..models.tag import Tag
from ..models.donor import Donor
from django.db.models import Q
import re
from functools import reduce
from operator import or_

SPLIT = r"\[|\]|-| |,"
archive_id_tag = re.compile(r"\[\s*([^\[\]]*[^\[\]\s]+)\s*-\s*(\d+)\s*\]")
id_tag = re.compile(r"\[\s*(\d+)\s*\]")


class ContributorSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self):
        txt = self.request.GET['term']
        clauses = []
        snip = 999999
        for match in re.finditer(archive_id_tag, txt):
            snip = min(snip, match.start())
            clauses.append(Q(id=int(match.group(2))))
        txt = txt[:snip]
        for s in re.split(SPLIT, txt):
            if s:
                try:
                    id = int(s)
                    clauses.append(Q(id=id))
                except ValueError:
                    clauses.append(Q(first_name__icontains=s))
                    clauses.append(Q(last_name__icontains=s))

        if clauses:
            return Donor.objects.filter(reduce(or_, clauses))[:20]

        else:
            return Donor.objects.none()

    def get_autocomplete_data(self, object):
        label = "{} [{}-{}]".format(object, object.archive.slug, object.id)
        return {'id': object.id, 'value': label, 'label': label}

    def get_data(self, context):
        return [
            self.get_autocomplete_data(object)
            for object in context['object_list']
        ]

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, safe=False, **kwargs)

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
