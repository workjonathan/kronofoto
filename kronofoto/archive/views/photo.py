from django.views.generic import DetailView
from django.http import Http404
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings
from django.template.loader import render_to_string
from .jsonresponse import JSONResponseMixin
from .basetemplate import BaseTemplateMixin
from .timelinepaginator import TimelinePaginator
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..reverse import get_request, set_request, as_absolute


NO_URLS = dict(url='#', json_url='#')


class PhotoView(JSONResponseMixin, BaseTemplateMixin, DetailView):
    items = 10
    pk_url_kwarg = 'photo'
    _queryset = None
    model = Photo

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def get_queryset(self):
        self.collection = CollectionQuery(self.final_expr, self.request.user)
        return Photo.objects.filter_photos(self.collection)

    #def get_object(self, *args, **kwargs):
    #    print("test")
    #    return self.model.objects.get(pk=self.model.accession2id(self.kwargs[self.pk_url_kwarg]))

    def get_paginator(self):
        return TimelinePaginator(self.queryset.order_by('year', 'id'), self.items)

    def get_context_data(self, **kwargs):
        context = super(PhotoView, self).get_context_data(**kwargs)
        if self.request.headers.get('Hx-Target', None) == 'fi-image':
            context['base_template'] = 'archive/photo_partial.html'
        photo = self.kwargs['photo']
        if 'page' in self.kwargs:
            page = self.kwargs['page']
        else:
            page = 1
        queryset = self.queryset
        cache_info = self.collection.cache_encoding()
        index_key = 'year_links:' + cache_info
        index = cache.get(index_key)
        if not index:
            index = queryset.year_links(params=self.request.GET)
            cache.set(index_key, index)

        paginator = self.get_paginator()
        page_selection = paginator.get_pages(page)

        try:
            photo_rec = page_selection.find(self.object.id)

            params = self.request.GET.copy()
            if 'constraint' in params:
                params.pop('constraint')
            for p in page_selection.photos():
                p.save_params(params)

            context['prev_page'], context["page"], context['next_page'] = page_selection.pages
            context['grid_url'] = photo_rec.get_grid_url()
            context['grid_json_url'] = photo_rec.get_grid_json_url()
            context["photo"] = photo_rec
            context["alttext"] = ', '.join(photo_rec.describe(self.request.user))
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
            context["years"] = index
            context['timeline_key'] = cache_info
            if self.request.user.is_staff and self.request.user.has_perm('archive.change_photo'):
                context['edit_url'] = photo_rec.get_edit_url()
            #context['initialstate'] = self.get_data(context)
        except KeyError:
            pass
        return context

    def get_data(self, context):
        if 'photo' not in context or not context['photo']:
            return {}
        photo = context['photo']
        return {
            'type': 'TIMELINE',
            'static_url': settings.STATIC_URL,
            'url': as_absolute(photo.get_absolute_url()),
            'h700': as_absolute(photo.h700.url),
            'alttext': str(context['alttext']),
            'tags': str(context['tags']),
            'original': photo.get_download_page_url(),
            'grid_json_url': photo.get_grid_json_url(),
            'timeline_json_url': context['timeline_json_url'],
            'grid_url': photo.get_grid_url(),
            'timeline_url': context['timeline_url'],
            'frame': render_to_string('archive/photo-details.html', context, self.request),
            'metadata': render_to_string('archive/photometadata.html', context, self.request),
            'thumbnails': render_to_string('archive/thumbnails.html', context, self.request),
            'backward': context['prev_page'][0].get_urls() if context['page'].has_previous() else NO_URLS,
            'forward': context['next_page'][0].get_urls() if context['page'].has_next() else NO_URLS,
            'previous': photo.previous.get_urls() if hasattr(photo, 'previous') else NO_URLS,
            'next': photo.next.get_urls() if hasattr(photo, 'next') else NO_URLS,
            'year': photo.year,
        }

    def render(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    def get_redirect_url(self, photo):
        return photo.get_absolute_url(queryset=self.queryset, params=self.request.GET)

    def render_to_response(self, context, **kwargs):
        if 'years' not in context:
            try:
                photo = Photo.objects.get(id=self.kwargs['photo'])
                return redirect(self.get_redirect_url(photo))
            except Photo.DoesNotExist:
                raise Http404("Photo either does not exist or is not in that set of photos")
        return self.render(context, **kwargs)


class JSONPhotoView(PhotoView):
    def get_data(self, context):
        return super().get_data(context)
    def render(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)
    def get_redirect_url(self, photo):
        return photo.get_json_url(queryset=self.queryset, params=self.request.GET)
