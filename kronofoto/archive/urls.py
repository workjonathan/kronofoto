from django.urls import path, include, register_converter
from . import views
from .views import collection, webcomponent, downloadpage
from django.views.generic.base import TemplateView
from archive.views.photosphere import PhotoSphereView
from archive.views.frontpage import RandomRedirect, YearRedirect
from archive.views.photo import TimelineSvg, CarouselListView
from archive.views.photo import LogoSvg, LogoSvgSmall
from archive.views.agreement import AgreementView
from archive.views.submission import SubmissionFormView, KronofotoTemplateView
from django.conf import settings

class NegativeIntConverter:
    regex = '-?\d+'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return "{}".format(value)

class AccessionNumberConverter:
    regex = r'FI\d+'

    def to_python(self, value):
        return int(value[2:])

    def to_url(self, value):
        return "FI" + str(value).zfill(7)

register_converter(NegativeIntConverter, 'negint')
register_converter(AccessionNumberConverter, 'accession')

app_name = 'kronofoto'
urlpatterns = [
    path('', views.RandomRedirect.as_view(), name='random-image'),
    path('timeline/<int:start>/<int:end>', TimelineSvg.as_view(), name='timelinesvg'),
    path('logo.svg/<str:theme>', LogoSvg.as_view(), name='logosvg'),
    path('logo-small.svg/<str:theme>', LogoSvgSmall.as_view(), name='logosvgsmall'),
    path('original/<int:photo>/', views.DownloadPageView.as_view()),
    path('photos/<accession:photo>/original', views.DownloadPageView.as_view(), name='download'),
    path('user/<str:username>/', views.Profile.as_view()),
    path('keyframes/<negint:origin>/<int:difference>/<int:step>/<str:unit>.css', views.Keyframes.as_view(), name='keyframes'),
    path('search/', views.GridView.as_view()),
    path('collection/', views.CollectionCreate.as_view()),
    path('collections', views.CollectionCreate.as_view(), name='collection-create'),
    path('collections/<int:pk>/delete', views.CollectionDelete.as_view(), name='collection-delete'),
    path('list/<str:photo>/', views.AddToList.as_view()),
    path('carousel', CarouselListView.as_view(item_count=40), name='carousel'),
    path('photos/<accession:photo>/list-members/edit', views.AddToList.as_view(), name='add-to-list'),
    path('photos/<accession:photo>/list-members', collection.ListMembers.as_view(), name='popup-add-to-list'),
    path('photos/<accession:photo>/list-members/new-list', collection.NewList.as_view(), name='popup-new-list'),
    path('photos/<accession:photo>/web-component', webcomponent.WebComponentPopupView.as_view(), name='popup-web-component'),
    path('photos/<accession:photo>/download', downloadpage.DownloadPopupView.as_view(), name='popup-download'),
    path('photo/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<accession:photo>', views.PhotoView.as_view(item_count=20), name="photoview"),
    path('photo/<int:page>/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<int:page>/<accession:photo>', views.PhotoView.as_view()),
    path('photo/year:<int:year>/', YearRedirect.as_view()),
    path('photos/year:<int:year>', YearRedirect.as_view()),
    path('photos/year', YearRedirect.as_view(), name="year-redirect"),
    path('mainstreet360/<int:pk>/', PhotoSphereView.as_view()),
    path('mainstreet360/<int:pk>', PhotoSphereView.as_view(), name="mainstreetview"),
    path('photo/<accession:photo>/tag-members/edit', views.AddTagView.as_view(), name='addtag'),
    path('tags', views.TagSearchView.as_view(), name='tag-search'),
    path('photos', views.GridView.as_view(), name='gridview'),
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
    path("<slug:short_name>/agreement", AgreementView.as_view(), name="agreement-create"),
    path("<slug:short_name>/photos/contribute", SubmissionFormView.as_view(), name="submission-create"),
    path("<slug:short_name>/photos/contribute/thanks", KronofotoTemplateView.as_view(template_name="archive/submission_received.html"), name="submission-done"),
    path("<slug:short_name>/", include(urlpatterns)),
]
