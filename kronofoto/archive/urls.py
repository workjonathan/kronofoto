from django.urls import path, include, register_converter, URLPattern, URLResolver
from . import views
from .views import collection, webcomponent, downloadpage
from django.views.generic.base import TemplateView
from archive.views.photosphere import PhotoSphereView, MainStreetList, MainStreetDetail, MainStreetGeojson
from archive.views.frontpage import RandomRedirect, YearRedirect
from archive.views.photo import TimelineSvg, CarouselListView
from archive.views.photo import LogoSvg, LogoSvgSmall
from archive.views.agreement import AgreementView
from archive.views.submission import SubmissionFormView, KronofotoTemplateView
from archive.views.tagsearch import ContributorSearchView
from archive.views.donor import ContributorCreateView
from archive.views import tags_view
from django.conf import settings
from typing import Sequence, Union, List


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

app_name = 'kronofoto'
urlpatterns : List[Union[URLPattern, URLResolver]] = [
    path('', views.RandomRedirect.as_view(category="photos"), name='random-image'),
    path('materials/<slug:category>/random', views.RandomRedirect.as_view(), name='random-image'),
    path('materials', views.category_list, name='materials-list'),
    path('timeline/<int:start>/<int:end>', TimelineSvg.as_view(), name='timelinesvg'),
    path('logo.svg/<str:theme>', LogoSvg.as_view(), name='logosvg'),
    path('logo-small.svg/<str:theme>', LogoSvgSmall.as_view(), name='logosvgsmall'),
    path('original/<int:photo>/', views.DownloadPageView.as_view()),
    path('photos/<accession:photo>/original', views.DownloadPageView.as_view(), name='download'),
    path('materials/all/<accession:pk>/original', views.DownloadPageView.as_view(pk_url_kwarg='pk'), name='download'),
    path('materials/<slug:category>/<accession:pk>/original', views.DownloadPageView.as_view(pk_url_kwarg='pk'), name='download'),
    path('user/<str:username>/', views.Profile.as_view()),
    path('keyframes/<negint:origin>/<int:difference>/<int:step>/<str:unit>.css', views.Keyframes.as_view(), name='keyframes'),
    path('search/', views.GridView.as_view()),
    path('collection/', views.CollectionCreate.as_view()),
    path('collections', views.CollectionCreate.as_view(), name='collection-create'),
    path('collections/<int:pk>/delete', views.CollectionDelete.as_view(), name='collection-delete'),
    path('list/<str:photo>/', views.AddToList.as_view()),
    path('materials/all/carousel', CarouselListView.as_view(item_count=40), name='carousel'),
    path('materials/<slug:category>/carousel', CarouselListView.as_view(item_count=40), name='carousel'),
    path('photos/<accession:photo>/list-members/edit', views.AddToList.as_view(), name='add-to-list'),
    path('materials/all/<accession:photo>/list-members/edit', views.AddToList.as_view(), name='add-to-list'),
    path('materials/<slug:category>/<accession:photo>/list-members/edit', views.AddToList.as_view(), name='add-to-list'),
    path('photos/<accession:photo>/list-members', collection.ListMembers.as_view(), name='popup-add-to-list'),
    path('photos/<accession:photo>/list-members/new-list', collection.NewList.as_view(), name='popup-new-list'),
    path('photos/<accession:photo>/web-component', webcomponent.WebComponentPopupView.as_view()),
    path('materials/all/<accession:photo>/web-component', webcomponent.WebComponentPopupView.as_view(), name='popup-web-component'),
    path('materials/<slug:category>/<accession:photo>/web-component', webcomponent.WebComponentPopupView.as_view(), name='popup-web-component'),
    path('photos/<accession:photo>/download', downloadpage.DownloadPopupView.as_view(), name='popup-download'),
    path('photo/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<accession:photo>', views.PhotoView.as_view(category='photos', item_count=20)),
    path('photo/<int:page>/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<int:page>/<accession:photo>', views.PhotoView.as_view()),
    path('photo/year:<int:year>/', YearRedirect.as_view(category="photos")),
    path('photos/year', YearRedirect.as_view(category="photos")),
    path('photos/year:<int:year>', YearRedirect.as_view(category="photos")),
    path('materials/all/<accession:photo>', views.PhotoView.as_view(), name="photoview"),
    path('materials/<slug:category>/<accession:photo>', views.PhotoView.as_view(), name="photoview"),
    path('materials/all/year', YearRedirect.as_view(), name="year-redirect"),
    path('materials/<slug:category>/year', YearRedirect.as_view(), name="year-redirect"),
    path('mainstreets', MainStreetList.as_view(), name='mainstreet-list'),
    path('mainstreets/<int:pk>', MainStreetDetail.as_view(), name='mainstreet-detail'),
    path('mainstreets/<int:pk>.geojson', MainStreetGeojson.as_view(), name='mainstreet-data'),
    path('mainstreet360/<int:pk>/', PhotoSphereView.as_view()),
    path('mainstreet360/<int:pk>', PhotoSphereView.as_view(), name="mainstreetview"),
    path('photos/<accession:photo>/tag-members', tags_view, name='tags-view'),
    path('materials/all/<accession:photo>/tag-members', tags_view, name='tags-view'),
    path('materials/<slug:category>/<accession:photo>/tag-members', tags_view, name='tags-view'),
    path('tags', views.TagSearchView.as_view(), name='tag-search'),
    path('autocomplete/contributors', ContributorSearchView.as_view(), name='contributor-search'),
    path('photos', views.GridView.as_view(category="photos")),
    path('materials/all', views.GridView.as_view(), name='gridview'),
    path('materials/<slug:category>', views.GridView.as_view(), name='gridview'),
    path('grid/<int:page>/', views.GridView.as_view()),
    path('photos/<int:page>', views.GridView.as_view()),
]

urlpatterns = urlpatterns + [
    path('users/<str:username>', views.Profile.as_view(), name='user-page'),
    path('about/', TemplateView.as_view(template_name='archive/about.html', extra_context={'title': 'About'}), name='about'),
    path('use/', TemplateView.as_view(template_name='archive/use.html', extra_context={'title': 'Use'}), name='use'),
    path('contribute/', TemplateView.as_view(template_name='archive/contribute.html', extra_context={'title': 'Contribute'}), name='contribute'),
    path('volunteer/', TemplateView.as_view(template_name='archive/volunteer.html', extra_context={'title': 'Volunteer'}), name='volunteer'),
    path('give/', TemplateView.as_view(template_name='archive/give.html', extra_context={'title': 'Give'}), name='give'),
    path('<slug:short_name>/contributors/add', ContributorCreateView.as_view(extra_context={"reason": "You must agree to terms before creating contributors."}), name='contributor-create'),
    path('<slug:short_name>/contributors/added', KronofotoTemplateView.as_view(template_name="archive/contributor_created.html"), name='contributor-created'),
    path("<slug:short_name>/agreement", AgreementView.as_view(), name="agreement-create"),
    path("<slug:short_name>/materials/contribute", SubmissionFormView.as_view(extra_context={"reason": "You must agree to terms before uploading."}), name="submission-create"),
    path("<slug:short_name>/materials/contribute/thanks", KronofotoTemplateView.as_view(template_name="archive/submission_received.html"), name="submission-done"),
    path("<slug:short_name>/", include(urlpatterns)),
]
