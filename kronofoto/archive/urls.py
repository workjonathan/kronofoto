from django.urls import path, include, register_converter, URLPattern, URLResolver
from . import views
from .views import collection, webcomponent, downloadpage
from django.views.generic.base import TemplateView
from archive.views.photosphere import PhotoSphereView, MainStreetList, MainStreetDetail, MainStreetGeojson
from archive.views.frontpage import RandomRedirect, YearRedirect
from archive.views.photo import TimelineSvg, CarouselListView
from archive.views.photo import LogoSvg, LogoSvgSmall
from archive.views.agreement import AgreementView
from archive.views.submission import submission, KronofotoTemplateView
from archive.views.tagsearch import ContributorSearchView
from archive.views.donor import ContributorCreateView
from archive.views import tags_view
from django.conf import settings
from django.http.response import HttpResponseBase
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple


class NegativeIntConverter:
    regex = '-?\d+'

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return "{}".format(value)

class AccessionNumberConverter:
    regex = r'FI\d+'

    def to_python(self, value: str) -> int:
        return int(value[2:])

    def to_url(self, value: int) -> str:
        return "FI" + str(value).zfill(7)

register_converter(NegativeIntConverter, 'negint')
register_converter(AccessionNumberConverter, 'accession')

def directory(
        route: str,
        view: Callable[..., HttpResponseBase],
        kwargs: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        children: Optional[Tuple[Sequence[Union[URLResolver, URLPattern]], Optional[str], Optional[str]]]=None,
    ) -> List[Union[URLPattern, URLResolver]]:
    full_kwargs : Dict[str, Any] = {}
    partial_kwargs : Dict[str, Any] = {}
    if kwargs:
        full_kwargs['kwargs'] = kwargs
        partial_kwargs['kwargs'] = kwargs
    if name:
        full_kwargs['name'] = name
    paths : List[Union[URLPattern, URLResolver]] = [
        path(route, view, **full_kwargs),
        path(route+"/", view, **partial_kwargs),
    ]
    if children:
        paths.append(path(route+"/", children))
    return paths

def build_content_urls(route: str, with_names: bool=False, kwargs: Optional[Dict[str, Any]] = None) -> List[Union[URLPattern, URLResolver]]:
    kwargs = kwargs or {}
    if with_names:
        get_kwargs : Callable[[str], Dict[str, Any]] = lambda x: {"kwargs": kwargs, "name": x}
    else:
        get_kwargs = lambda x: {"kwargs": kwargs}
    return directory(route, views.GridView.as_view(), **get_kwargs("gridview"), children=include([
        *directory('<accession:photo>', views.PhotoView.as_view(), **get_kwargs("photoview"), children=include([
            path('original', views.DownloadPageView.as_view(pk_url_kwarg='photo'), **get_kwargs('download')),
            *directory('list-members', collection.ListMembers.as_view(), **get_kwargs('popup-add-to-list'), children=include([
                path('new-list', collection.NewList.as_view(), **get_kwargs('popup-new-list')),
                path('edit', views.AddToList.as_view(), **get_kwargs('add-to-list')),
            ])),
            path('web-component', webcomponent.WebComponentPopupView.as_view(), **get_kwargs('popup-web-component')),
            path('tag-members', tags_view, **get_kwargs('tags-view')),
            path('download', downloadpage.DownloadPopupView.as_view(), **get_kwargs('popup-download')),
        ])),
        path('data.json', views.datadump, **get_kwargs('data-dump')),
        path('random', views.RandomRedirect.as_view(), **get_kwargs('random-image')),
        path('carousel', CarouselListView.as_view(item_count=40), **get_kwargs('carousel')),
        path('download', downloadpage.DownloadPopupView.as_view(), **get_kwargs('popup-download')),
        path('year', YearRedirect.as_view(), **get_kwargs("year-redirect")),
    ]))

app_name = 'kronofoto'
urlpatterns : List[Union[URLPattern, URLResolver]] = [
    path('', views.RandomRedirect.as_view(category="photos"), name='random-image'),
    *build_content_urls("photos", with_names=False, kwargs={"category": "photos"}),
    *directory('categories', views.category_list, name="materials-list", children=include([
        *build_content_urls("all", with_names=True, kwargs={}),
        *build_content_urls("<slug:category>", with_names=True, kwargs={}),
    ])),
    *directory('materials', views.category_list, name="materials-list", children=include([
        *build_content_urls("all", with_names=False, kwargs={}),
        *build_content_urls("<slug:category>", with_names=False, kwargs={}),
    ])),
    path('logo.svg/<str:theme>', LogoSvg.as_view()),
    path('logo-small.svg/<str:theme>', LogoSvgSmall.as_view()),
    path('<str:theme>/logo.svg', LogoSvg.as_view(), name='logosvg'),
    path('<str:theme>/logo-small.svg', LogoSvgSmall.as_view(), name='logosvgsmall'),
    *directory('collections', views.CollectionCreate.as_view(), name='collection-create', children=include([
        path('<int:pk>/delete', views.CollectionDelete.as_view(), name='collection-delete'),
    ])),
    *directory('mainstreets', MainStreetList.as_view(), name='mainstreet-list', children=include([
        path('<int:pk>', MainStreetDetail.as_view(), name='mainstreet-detail'),
        path('<int:pk>.geojson', MainStreetGeojson.as_view(), name='mainstreet-data'),
    ])),
    path('mainstreet360/<int:pk>', PhotoSphereView.as_view(), name="mainstreetview"),
    path('mainstreet360/<int:pk>.json', views.photosphere_data, name="mainstreetview.json"),
    path('tags', views.TagSearchView.as_view(), name='tag-search'),
    path('autocomplete/contributors/select2', views.contributor_search, name='contributor-search2'),
    path('autocomplete/contributors', ContributorSearchView.as_view(), name='contributor-search'),
    path('autocomplete/places', views.place_search, name='place-search'),
    path('autocomplete/places/all', views.place_search, {"require_photo": False}, name='all-place-search'),
]

urlpatterns = urlpatterns + [
    path('users/<str:username>', views.Profile.as_view(), name='user-page'),
    path('about/', TemplateView.as_view(template_name='archive/about.html', extra_context={'title': 'About'}), name='about'),
    path('use/', TemplateView.as_view(template_name='archive/use.html', extra_context={'title': 'Use'}), name='use'),
    path('contribute/', TemplateView.as_view(template_name='archive/contribute.html', extra_context={'title': 'Contribute'}), name='contribute'),
    path('volunteer/', TemplateView.as_view(template_name='archive/volunteer.html', extra_context={'title': 'Volunteer'}), name='volunteer'),
    path('give/', TemplateView.as_view(template_name='archive/give.html', extra_context={'title': 'Give'}), name='give'),
    path('user/<str:username>/', views.Profile.as_view()),
    path('<slug:short_name>/contributors/add', ContributorCreateView.as_view(), name='contributor-create'),
    path('<slug:short_name>/contributors/added', KronofotoTemplateView.as_view(template_name="archive/contributor_created.html"), name='contributor-created'),
    path("<slug:short_name>/agreement", AgreementView.as_view(), name="agreement-create"),
    path("<slug:short_name>/materials/contribute", views.submission),
    path("<slug:short_name>/materials/contribute/thanks", KronofotoTemplateView.as_view(template_name="archive/submission_received.html")),
    path("<slug:short_name>/contribute", views.submission, name="submission-create"),
    path("<slug:short_name>/contribute/terms", views.list_terms, name="term-list"),
    path("<slug:short_name>/contribute/terms/define", views.define_terms, name="define-terms"),
    path("<slug:short_name>/contribute/thanks", KronofotoTemplateView.as_view(template_name="archive/submission_received.html"), name="submission-done"),
    path("<slug:short_name>/", include(urlpatterns)),
    path(settings.IMAGE_CACHE_URL_PREFIX + "images/<int:block1>/<int:block2>/<str:profile1>.jpg", views.resize_image, name="resize-image"),
    path("exhibit-test", views.exhibit),
]
