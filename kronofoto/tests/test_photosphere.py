from fortepan_us.kronofoto.views.photosphere import ValidPhotoSphereView
from fortepan_us.kronofoto.models import PhotoSphere, MainStreetSet, PhotoSphereTour, Photo
from hypothesis import given, strategies as st
from django.test import RequestFactory
from string import printable
from django.contrib.gis.geos import Point


@given(
    view=st.builds(
        ValidPhotoSphereView,
        pk=st.integers(),
        request=st.just(RequestFactory().get("/")),
    ),
    object=st.builds(
        PhotoSphere,
        mainstreetset=st.one_of(st.none(), st.builds(MainStreetSet, id=st.integers(min_value=1), name=st.text(printable))),
        location=st.one_of(st.none(), st.builds(Point, st.integers(), st.integers())),
    ),
    photo=st.one_of(st.none(), st.builds(Photo)),
    domain=st.text(printable, min_size=1).map(lambda s: s + ".com"),
)
def test_photosphere_response(view, object, domain, photo):
    view.object = object
    view.domain = domain
    view.nearby_mainstreets = []
    view.photo = photo
    view.response
