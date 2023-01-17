from django.urls import path, include, register_converter
from . import views
from django.views.generic.base import TemplateView
from archive.views.photosphere import PhotoSphereView
from archive.views.frontpage import RandomRedirect, YearRedirect
from archive.views.photo import TimelineSvg

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

urlpatterns = [
    path('', views.RandomRedirect.as_view(), name='random-image'),
    path('missing-photos/', views.MissingPhotosView.as_view()),
    path('<str:id>.css', views.EmbedStyleSheet.as_view(), name="css"),
    path('about/', TemplateView.as_view(template_name='archive/about.html', extra_context={'title': 'About'}), name='about'),
    path('timeline/<int:start>/<int:end>', TimelineSvg.as_view(), name='timelinesvg'),
    path('use/', TemplateView.as_view(template_name='archive/use.html', extra_context={'title': 'Use'}), name='use'),
    path('contribute/', TemplateView.as_view(template_name='archive/contribute.html', extra_context={'title': 'Contribute'}), name='contribute'),
    path('volunteer/', TemplateView.as_view(template_name='archive/volunteer.html', extra_context={'title': 'Volunteer'}), name='volunteer'),
    path('original/<int:pk>/', views.DownloadPageView.as_view(), name='download'),
    path('give/', TemplateView.as_view(template_name='archive/give.html', extra_context={'title': 'Give'}), name='give'),
    path('accounts/', include('archive.auth.urls')),
    path('user/<str:username>/', views.Profile.as_view(), name='user-page'),
    path('keyframes/<negint:origin>/<int:difference>/<int:step>/<str:unit>.css', views.Keyframes.as_view(), name='keyframes'),
    path('search/', views.SearchResultsView.as_view(), name='search-results'),
    path('search.json', views.JSONSearchResultsView.as_view(), name='search-results-json'),
    path('directory/', views.DirectoryView.as_view(), name='directory'),
    path('collection/', views.CollectionCreate.as_view(), name='collection-create'),
    path('collection/<int:pk>/delete', views.CollectionDelete.as_view(), name='collection-delete'),
    path('list/<str:photo>/', views.AddToList.as_view(), name='add-to-list'),
    path('photo/<accession:photo>/', views.PhotoView.as_view(), name="photoview"),
    path('photo/<int:page>/<accession:photo>/', views.PhotoView.as_view(), name="photoview"),
    path('photo/<int:page>/<accession:photo>.json', views.JSONPhotoView.as_view(), name="photoview-json"),
    path('photo/year:<int:year>/', YearRedirect.as_view(), name="year-redirect"),
    path('mainstreet360/<int:pk>/', PhotoSphereView.as_view(), name="mainstreetview"),
    path('tag/<str:photo>/', views.AddTagView.as_view(), name='addtag'),
    path('tags/', views.TagSearchView.as_view(), name='tag-search'),
    path('grid/', views.GridView.as_view(), name='gridview'),
    path('grid.json', views.JSONGridView.as_view(), name='gridview-json'),
    path('grid/<int:page>/', views.GridView.as_view(), name='gridview'),
    path('grid/<int:page>.json', views.JSONGridView.as_view(), name='gridview-json'),
    path('publish/', views.PrePublishPhotoList.as_view(), name='prepublishlist'),
    path('upload/', views.UploadScannedImage.as_view(), name="upload"),
    path('review/', views.ReviewPhotos.as_view(), name="review"),
    path('publish/<int:pk>', views.PrePublishPhotoView.as_view(), name='prepublishdetails'),
    path('publish/<int:pk>/approve', views.PublishPhotoRedirect.as_view(publish=True), name='approve'),
    path('publish/<int:pk>/reject', views.PublishPhotoRedirect.as_view(publish=False), name='reject'),
    path('review/<int:pk>/vote/yes', views.VoteOnPhoto.as_view(infavor=True), name='photo-yes'),
    path('review/<int:pk>/vote/no', views.VoteOnPhoto.as_view(infavor=False), name='photo-no'),
    path('review/<int:pk>/approve/yes', views.ApprovePhoto.as_view(approve=True), name='photo-approve'),
    path('review/<int:pk>/approve/no', views.ApprovePhoto.as_view(approve=False), name='photo-reject'),
]
