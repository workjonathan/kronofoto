from __future__ import annotations
from django.test import TestCase
from hypothesis import given, strategies as st, settings as hsettings
from fortepan_us.kronofoto.views.vector_tiles import PhotoSphereTile
from django.contrib.gis.geos import Point, Polygon
from fortepan_us.kronofoto.models import PhotoSphere, MainStreetSet, PhotoSphereTour
from dataclasses import dataclass
import pytest

class TestPhotoSphereFiltering(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sets = [
            None,
            MainStreetSet.objects.create(name="set one"),
            MainStreetSet.objects.create(name="set two"),
        ]
        cls.tours = [
            None,
            PhotoSphereTour.objects.create(name="tour one"),
            PhotoSphereTour.objects.create(name="tour two"),
        ]
        for tour in cls.tours:
            for mainstreet in cls.sets:
                PhotoSphere.objects.create(
                    mainstreetset=mainstreet,
                    tour=tour,
                    location=Point(-1,1),
                )

    def test_tourfilter(self):
        photospheres = PhotoSphereTile(
            x=0,
            y=0,
            zoom=1,
            mainstreet=self.sets[1].id,
            tour=self.tours[1].id,
        ).photospheres
        assert photospheres.count() == 1

    def test_notourfilter(self):
        photospheres = PhotoSphereTile(
            x=0,
            y=0,
            zoom=1,
            mainstreet=self.sets[1].id,
            tour=None,
        ).photospheres
        assert photospheres.count() == 3



@dataclass
class TestTile(PhotoSphereTile):
    _photospheres: list[PhotoSphere]

    @property
    def photospheres(self) -> list[PhotoSphere]:
        bbox = self.bbox
        return [sphere for sphere in self._photospheres if sphere.location.within(bbox)]

@hsettings(max_examples=10)
@given(
    pst=st.builds(
        TestTile,
        x=st.integers(min_value=1, max_value=1),
        y=st.integers(min_value=1, max_value=3),
        zoom=st.integers(min_value=0, max_value=34),
        mainstreet=st.integers(),
        tour=st.one_of(st.none(), st.integers()),
        _photospheres = st.lists(
            st.builds(
                PhotoSphere,
                id=st.integers(min_value=1, max_value=1000),
                location=st.builds(Point, st.floats(min_value=-1000, max_value=1000), st.floats(min_value=-1000, max_value=1000)),
            )),
    ),
)
def test_layers(pst):
    pst.response

@given(
    pst=st.builds(
        PhotoSphereTile,
        x=st.integers(min_value=-10, max_value=10),
        y=st.integers(min_value=-10, max_value=10),
        zoom=st.integers(min_value=1, max_value=34),
        mainstreet=st.integers(),
        tour=st.one_of(st.none(), st.integers()),
    ),
)
def test_bounds(pst):
    pst.bounds
    pst.bbox
