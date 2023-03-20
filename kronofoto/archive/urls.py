from django.urls import path, include, register_converter
from . import views
from .views import collection
from django.views.generic.base import TemplateView
from archive.views.photosphere import PhotoSphereView
from archive.views.frontpage import RandomRedirect, YearRedirect
from archive.views.photo import TimelineSvg
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
    path('original/<int:pk>/', views.DownloadPageView.as_view()),
    path('photos/<accession:pk>/original', views.DownloadPageView.as_view(), name='download'),
    path('user/<str:username>/', views.Profile.as_view()),
    path('keyframes/<negint:origin>/<int:difference>/<int:step>/<str:unit>.css', views.Keyframes.as_view(), name='keyframes'),
    path('search/', views.GridView.as_view()),
    path('collection/', views.CollectionCreate.as_view()),
    path('collections', views.CollectionCreate.as_view(), name='collection-create'),
    path('collections/<int:pk>/delete', views.CollectionDelete.as_view(), name='collection-delete'),
    path('list/<str:photo>/', views.AddToList.as_view()),
    path('photos/<accession:photo>/list-members/edit', views.AddToList.as_view(), name='add-to-list'),
    path('photos/<accession:photo>/list-members', collection.ListMembers.as_view(), name='popup-add-to-list'),
    path('photo/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<accession:photo>', views.PhotoView.as_view(), name="photoview"),
    path('photo/<int:page>/<accession:photo>/', views.PhotoView.as_view()),
    path('photos/<int:page>/<accession:photo>', views.PhotoView.as_view()),
    path('photo/year:<int:year>/', YearRedirect.as_view()),
    path('photos/year:<int:year>', YearRedirect.as_view(), name="year-redirect"),
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
    path("<slug:short_name>/", include(urlpatterns)),
]
