from .frontpage import RandomRedirect
from .basetemplate import BaseTemplateMixin
from .addtag import tags_view
from .paginator import TimelinePaginator, EMPTY_PNG, FAKE_PHOTO, FakeTimelinePage
from .photo import PhotoView
from .photosphere import photosphere_data, photosphere_view
from .downloadpage import DownloadPageView
from .tagsearch import TagSearchView, contributor_search, place_search
from .directory import DirectoryView
from .collection import AddToList, CollectionDelete, profile_view, collections_view, collection_view
from .grid import GridView
from .categories import category_list
from .submission import submission, list_terms, define_terms
from .exhibit import view as exhibit_view, exhibit_list, exhibit_create, exhibit_edit, exhibit_card_form, exhibit_figure_form, exhibit_images, exhibit_figure_image, exhibit_full_image, exhibit_two_column_image
from .images import resize_image
from .data import datadump
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.models import Photo
from django.template.response import TemplateResponse
from .map import map_list, map_detail

def attribution(request: HttpRequest) -> HttpResponse:
    html_name = request.GET.get("html_name", "")
    try:
        photo_id = int(request.GET.get(html_name, ""))
        photo = get_object_or_404(Photo.objects.all(), pk=photo_id)
        context = {
            "form": True,
            "edit": True,
            "object": photo,
        }
        return TemplateResponse(request=request, context=context, template="kronofoto/components/attribution.html")
    except ValueError:
        return HttpResponse("", status=400)
