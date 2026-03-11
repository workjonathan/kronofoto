from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase, from_model
from fortepan_us.kronofoto.models.place import Place, PlaceType
from django.db import transaction

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
                node = Place.objects.create(
                    id=i+1, place_type=place_types[pti], parent=parent, name="{i}", fullname=f"{i}",
                )
                nodes.append(node)
        Place.objects.rebuild()
    return nodes

@st.composite
def places(draw):
    pt = draw(st.lists(from_model(PlaceType), unique_by=lambda p: p.name, min_size=1))
    structure = draw(random_tree())
    places = draw(build_tree(structure, pt))
    return (places, pt, structure)

class TestImport(TestCase):
    @given(places())
    def test_fail(self, places):
        for p in Place.objects.all():
            assert p.get_children().count() < 4
