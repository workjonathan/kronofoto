from __future__ import annotations
from hypothesis import given, strategies as st
from fortepan_us.kronofoto.views.vector_tiles import PhotoSphereTile
from django.contrib.gis.geos import Point, Polygon
from fortepan_us.kronofoto.models import PhotoSphere
from dataclasses import dataclass

@dataclass
class TestTile(PhotoSphereTile):
    _photospheres: list[PhotoSphere]

    @property
    def photospheres(self) -> list[PhotoSphere]:
        bbox = self.bbox
        return [sphere for sphere in self._photospheres if sphere.location.within(bbox)]

@given(
    pst=st.builds(
        TestTile,
        x=st.integers(min_value=-10, max_value=10),
        y=st.integers(min_value=-10, max_value=10),
        zoom=st.integers(min_value=1, max_value=34),
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
