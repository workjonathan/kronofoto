from hypothesis import given, strategies as st, assume, settings
from hypothesis.extra.django import TestCase, from_model
from fortepan_us.kronofoto.models.place import Place, PlaceType
from django.db import transaction
import shapely

@st.composite
def convex_hulls(draw):
    points = draw(st.lists(st.tuples(st.integers(min_value=-180, max_value=180), st.integers(min_value=-90, max_value=90)), min_size=3, max_size=20, unique=True))
    hull = shapely.convex_hull(shapely.MultiPoint([shapely.Point(point) for point in points]))
    assume(hull.area > 0)
    return hull


@st.composite
def random_tree(draw, max_nodes=50):
    n = draw(st.integers(min_value=1, max_value=max_nodes))

    parents = []

    for i in range(n):
        parent = draw(st.one_of(
            st.none(),
            st.integers(min_value=0, max_value=i-1) if i > 0 else st.none()
        ))
        parents.append(parent)

    return parents

@st.composite
def build_tree(draw, structure, place_types):
    nodes = []
    with transaction.atomic():
        with Place.objects.disable_mptt_updates():
            for i, parent_index in enumerate(structure):
                parent = nodes[parent_index] if parent_index else None
                pti = draw(st.integers(0, len(place_types)-1))
                geom = draw(st.one_of(st.none(), convex_hulls().map(lambda h: h.wkt)))
                node = Place.objects.create(
                    id=i+1, place_type=place_types[pti], parent=parent, name="{i}", fullname=f"{i}", geom=geom,
                )
                nodes.append(node)
        Place.objects.rebuild()
    return nodes

@st.composite
def places(draw):
    pt = draw(st.lists(from_model(PlaceType, name=st.text(min_size=1)), unique_by=lambda p: p.name, min_size=1))
    parent_place_type_index = draw(st.integers(min_value=0, max_value=len(pt) - 1))
    new_place_type_index = draw(st.integers(min_value=0, max_value=len(pt) - 1))
    structure = draw(random_tree())
    places = draw(build_tree(structure, pt))
    return (places, pt, structure, pt[parent_place_type_index], pt[new_place_type_index])

osm_polys = lambda: st.tuples(
    st.text(min_size=1), # name
    convex_hulls(), # geometry
    st.dictionaries( # other tags
        keys=st.sampled_from(["de", "en", "fr", "es"]).map(lambda s: "name:"+s),
        values=st.text(),
    ),
)

class TestImport(TestCase):
    @settings(deadline=None)
    @given(places(), st.lists(osm_polys()))
    def test_fail(self, places, new_places):
        places, pts, structure, parent_type, new_type = places
        created, no_parents, multiple_parents = Place.objects.osm_import(import_data=new_places, new_place_type=new_type, parent_place_type=parent_type)
        assert len(created) + len(no_parents) + len(multiple_parents) == len(new_places)
