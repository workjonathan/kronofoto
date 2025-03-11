from fortepan_us.kronofoto.views.photosphere import ValidPhotoSphereView
from fortepan_us.kronofoto.models import PhotoSphere, MainStreetSet, PhotoSphereTour, Photo, Archive, Category, PhotoSpherePair, Donor, PhotoSphereInfo
from hypothesis import given, strategies as st, provisional
from django.test import RequestFactory
from string import printable
from django.contrib.gis.geos import Point
from django.test import TestCase
from unittest.mock import Mock


class TestPhotoSphereMainStreetFiltering(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sets = [
            MainStreetSet.objects.create(name="set one"),
            MainStreetSet.objects.create(name="set two"),
        ]
        cls.tours = [
            None,
            PhotoSphereTour.objects.create(name="tour two"),
        ]
        archive = Archive.objects.create()
        category = Category.objects.create()
        donor = Donor.objects.create(archive=archive)
        cls.photospheres = []
        for tour, mainstreet in zip(cls.tours, cls.sets):
            photosphere = PhotoSphere.objects.create(
                mainstreetset=mainstreet,
                tour=tour,
                location=Point(1, 1),
                is_published=True
            )
            photo = Photo.objects.create(
                archive=archive,
                category=category,
                year=1950,
                is_published=True,
                donor=donor,
            )
            PhotoSpherePair.objects.create(photosphere=photosphere, photo=photo)
            cls.photospheres.append(photosphere)



    def test_photosphere_object(self):
        viewer = ValidPhotoSphereView(
            pk=self.photospheres[0].id,
            request=None,
        )
        assert viewer.object == self.photospheres[0]

    def test_mainstreet_publishedfiltering(self):
        self.photospheres[1].is_published = False
        self.photospheres[1].save()
        viewer = ValidPhotoSphereView(
            pk=self.photospheres[0].id,
            request=None,
        )
        assert viewer.nearby_mainstreets.count() == 1
        assert viewer.nearby.count() == 1

    def test_mainstreet_filtering(self):
        viewer = ValidPhotoSphereView(
            pk=self.photospheres[0].id,
            request=None,
        )
        assert viewer.nearby_mainstreets.count() == 2
        assert viewer.nearby.count() == 1

    def test_mainstreet_tour_filtering(self):
        viewer = ValidPhotoSphereView(
            pk=self.photospheres[-1].id,
            request=None,
        )
        assert viewer.nearby_mainstreets.count() == 1
        assert viewer.nearby.count() == 1

@given(
    image_url=st.builds(Mock, return_value=st.text(printable, max_size=10)),
    dimensions=st.builds(Mock, return_value=st.tuples(st.integers(min_value=1), st.integers(min_value=1))),
    view=st.builds(
        ValidPhotoSphereView,
        pk=st.integers(),
        request=st.just(RequestFactory().get("/")),
    ),
    object=st.builds(
        PhotoSphere,
        mainstreetset=st.one_of(st.none(), st.builds(MainStreetSet, id=st.integers(min_value=1), name=st.text(printable, max_size=10))),
        tour=st.one_of(st.none(), st.builds(PhotoSphereTour, id=st.integers(min_value=1), name=st.text(printable, max_size=10))),
        location=st.one_of(st.none(), st.builds(Point, st.integers(), st.integers())),
        image=st.one_of(st.builds(Mock, name=st.text(printable, max_size=10), url=st.text(printable, max_size=10))),
    ),
    links=st.lists(st.builds(PhotoSphere, id=st.integers(min_value=1), location=st.builds(Point, st.integers(), st.integers())), max_size=3),
    related_photosphere_pairs=st.lists(
        st.builds(
            PhotoSpherePair,
            photo=st.builds(
                Photo,
                id=st.integers(min_value=1),
                original=st.builds(Mock, name=st.text(printable, max_size=10), url=st.text(printable, max_size=10)),
                original_width=st.integers(min_value=1),
                original_height=st.integers(min_value=1),
            ),
            photosphere=st.builds(PhotoSphere, id=st.integers(min_value=1), image=st.builds(Mock, name=st.text(printable, max_size=10), url=st.text(printable, max_size=10))),
            azimuth=st.integers(), inclination=st.integers(), distance=st.integers(),
        ),
        max_size=4,
    ),
    infoboxes=st.lists(st.builds(PhotoSphereInfo, id=st.integers(min_value=1), yaw=st.integers(), pitch=st.integers()), max_size=4),
    photo=st.one_of(st.none(), st.builds(Photo, id=st.integers(min_value=1))),
)
def test_photosphere_json_response(view, object, photo, links, related_photosphere_pairs, infoboxes, image_url, dimensions):
    view.object = object
    view.links = links
    view.related_photosphere_pairs = related_photosphere_pairs
    view.infoboxes = infoboxes
    view.photo = photo
    view.dimensions = dimensions
    view.image_url = image_url
    view.json_response


@given(
    view=st.builds(
        ValidPhotoSphereView,
        pk=st.integers(),
        request=st.just(RequestFactory().get("/")),
    ),
    object=st.builds(
        PhotoSphere,
        mainstreetset=st.one_of(st.none(), st.builds(MainStreetSet, id=st.integers(min_value=1), name=st.text(printable))),
        tour=st.one_of(st.none(), st.builds(PhotoSphereTour, id=st.integers(min_value=1), name=st.text(printable))),
        location=st.one_of(st.none(), st.builds(Point, st.integers(), st.integers())),
    ),
    photo=st.one_of(st.none(), st.builds(Photo)),
    nearby_photo=st.one_of(st.none(), st.builds(Photo)),
    domain=st.text(printable, min_size=1).map(lambda s: s + ".com"),
    nearby_mainstreets=st.lists(st.builds(Mock, closest=st.integers(min_value=1))),
)
def test_photosphere_response(view, object, domain, photo, nearby_mainstreets, nearby_photo):
    view.object = object
    view.domain = domain
    view.nearby_mainstreets = nearby_mainstreets
    view.photo = photo
    view.nearby_photo = nearby_photo
    view.photosphere_pair = lambda id: Mock(**{"photosphere.get_absolute_url()": "https://www.example.com"})
    view.response
