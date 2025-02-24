import pytest
import requests
from fortepan_us.kronofoto.reverse import reverse
from unittest import mock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, override_settings
from hypothesis import given, strategies as st, note, settings as hsettings, provisional, assume
from hypothesis.extra.django import TestCase, from_model
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, OutboxActivity
from fortepan_us.kronofoto import models
from fortepan_us.kronofoto.views.activitypub import decode_signature, decode_signature_headers, SignatureHeaders, Contact, Image
from fortepan_us.kronofoto.views import activitypub
import json
from django.core.cache import cache
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from datetime import datetime, timezone
import base64
import hashlib
from .util import photos, donors, archives, archives, small_gif, a_photo, a_category, an_archive, a_donor
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from fortepan_us.kronofoto.models.activity_dicts import ActivitypubImage, ActivitypubContact, ActivitypubLocation, Url
from django.contrib.gis.geos import Polygon, MultiPolygon, Point

st.register_type_strategy(Point, st.builds(Point, st.tuples(st.floats(allow_nan=False), st.floats(allow_nan=False))))
st.register_type_strategy(Polygon, st.builds(Polygon, st.lists(st.tuples(st.floats(allow_nan=False), st.floats(allow_nan=False)), min_size=3).map(lambda lst: lst + [lst[0]])))
st.register_type_strategy(MultiPolygon, st.builds(MultiPolygon, st.lists(st.from_type(Polygon), min_size=1)))
st.register_type_strategy(Url, provisional.urls())

@given(
    actor=st.builds(models.RemoteActor),
    place_type=st.builds(models.PlaceType),
    ldid=st.builds(models.LdId, content_object=st.one_of(st.none(), st.builds(models.Place))),
    location=st.from_type(ActivitypubLocation),
)
def test_create_place(location, actor, ldid, place_type):
    from fortepan_us.kronofoto.models.ldid import UpdateLdIdPlace
    upserter = UpdateLdIdPlace(ld_id=ldid, owner=actor, object=location)
    upserter.place_type = place_type
    if ldid.content_object:
        ldid.content_object.save = mock.Mock()
    upserter.result



class TestDonorReconcile(TestCase):
    @hsettings(max_examples=10)
    @given(st.from_type(ActivitypubContact), archives())
    def test_donor_reconcile(self, data, archive):
        donor = models.Donor()
        donor.archive = archive
        donor.reconcile(data)
        assert models.Donor.objects.filter(first_name=data['firstName'], last_name=data['lastName']).exists()


def test_decode_signature():
    signature = 'keyId="https://my-example.com/actor#main-key",headers="(request-target) host date digest",signature="asdf"'
    assert decode_signature(signature) == {
        "keyId": "https://my-example.com/actor#main-key",
        "headers": "(request-target) host date digest",
        "signature": "asdf",
    }

def test_decode_signature_headers():
    signature_headers = "(request-target) host date digest"
    assert decode_signature_headers(signature_headers) == [
        "(request-target)", "host", "date", "digest"
    ]

@pytest.mark.django_db
def test_service_actor_key_can_be_accessed():
    actor = models.ServiceActor.get_instance()
    actor.keyId

@pytest.mark.django_db
def test_service_actor_key_is_idempotent():
    actor = models.ServiceActor.get_instance()
    assert actor.guaranteed_public_key() == actor.guaranteed_public_key()


@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_archive_get_or_create_by_profile_for_local_archive(an_archive):
    # When could this happen?
    with mock.patch('requests.get') as mock_:
        archive, created = models.Archive.objects.get_or_create_by_profile("http://example.com/kf/activitypub/archives/aslug")
        assert not created
        assert archive.id == an_archive.id
        mock_.assert_not_called()

from string import printable
jsons = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(printable),
    lambda children: st.lists(children) | st.dictionaries(st.text(printable), children),
)

@given(
    force_id_match=st.booleans(),
    archive=st.one_of(st.none(), st.just(models.Archive())),
    ldid=st.one_of(
        st.tuples(
            st.text("abcdefg", min_size=1), st.integers(min_value=1)
        ).map(lambda s: reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={"short_name": s[0], "pk": s[1]}, domain="example.com")),
        provisional.urls(),
    ),
    created_ldid=st.builds(models.LdId, content_object=st.just(models.Donor())),
    remote_data=st.fixed_dictionaries({
        "type": st.just("Contact"),
    }, optional={
        "id": st.text(printable),
        "attributedTo": st.lists(st.text(printable), max_size=3),
    }),
)
def test_ldid_get_or_create_ld_donor(ldid, remote_data, force_id_match, archive, created_ldid):
    from fortepan_us.kronofoto.models.ldid import LdDonorGetOrCreator
    if force_id_match:
        remote_data['attributedTo'] = [ldid]
    obj = LdDonorGetOrCreator(ld_id=ldid, queryset=models.LdId.objects.all(), data=remote_data)
    obj.archive = archive
    obj.reconcile = mock.Mock()
    obj.ldid = mock.Mock(return_value=created_ldid)
    ldid, created = obj.object


@override_settings(KF_URL_SCHEME="http:")
@given(
    is_local=st.booleans(),
    force_id_match=st.booleans(),
    existing_ldid=st.one_of(st.none(), st.builds(models.LdId, content_object=st.one_of(st.none(), st.builds(models.Donor)))),
    resolved_donor=st.one_of(st.none(), st.builds(models.Donor)),
    ldid=st.one_of(
        st.tuples(
            st.text("abcdefg", min_size=1), st.integers(min_value=1)
        ).map(lambda s: reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={"short_name": s[0], "pk": s[1]}, domain="example.com")),
        provisional.urls(),
    ),
    #remote_data=st.one_of(st.from_type(ActivitypubContact), jsons),
    remote_data=st.one_of(st.none(), st.fixed_dictionaries({}, optional={"id": st.text(printable), "type": st.one_of(st.just("Contact"), st.text(printable))})),
    remote_processor=st.one_of(st.none(), st.just((None, False)), st.builds(models.LdId, content_object=st.just(models.Donor())).map(lambda ldid: (ldid, True))),
)
def test_ldid_get_or_create_ld_object(ldid, is_local, existing_ldid, remote_data, resolved_donor, force_id_match, remote_processor):
    from fortepan_us.kronofoto.models.ldid import LdObjectGetOrCreator
    obj = LdObjectGetOrCreator(ld_id=ldid, queryset=models.LdId.objects.all())
    obj.is_local = is_local
    obj.existing_ldid = existing_ldid
    if obj.existing_ldid is not None:
        obj.existing_ldid.delete = mock.Mock()
    if isinstance(remote_data, dict):
        if force_id_match:
            remote_data['id'] = ldid
    obj.remote_data = remote_data
    obj.resolved_donor = resolved_donor
    obj.donorgetorcreate = mock.Mock()
    if remote_processor is None:
        obj.donorgetorcreate.return_value = None
    else:
        obj.donorgetorcreate().object = remote_processor
    ldid, created = obj.object
    if not obj.is_local and obj.existing_ldid is not None and obj.existing_ldid.content_object is None:
        obj.existing_ldid.delete.assert_called()


@pytest.mark.django_db
def test_archive_get_or_create_encounters_insufficient_information():
    with mock.patch('requests.get') as mock_:
        mock_.return_value = mock.Mock(name="json")
        mock_.return_value.json.return_value = {
            "id": "https://example2.com/remotesite",
            "type": "Organization",
        }
        assert models.Archive.objects.get_or_create_by_profile(profile="https://example2.com/remotesite") == (None, False)

@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_ignore_activities_from_nonfollows(a_donor):
    remote_archive = Archive.objects.create(slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=False))
    data=activitypub.ActivitySchema().dump({
        "actor": remote_archive,
        "object": a_donor,
        "type": "Create",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    })
    remote_archive.delete()
    request = RequestFactory().post(
        "/kf/activitypub/service/inbox",
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        headers={
            "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
        data=json.dumps(data),
    )
    request.actor = remote_archive.actor
    Site.objects.all().update(domain='example2.net')
    models.Donor.objects.all().delete()
    resp = activitypub.service_inbox(request)
    assert resp.status_code == 401
    assert not models.Donor.objects.all().exists()


@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_receiving_a_photo_update_updates_a_photo(a_photo, a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    a_photo.archive = remote_archive
    a_photo.caption = "old caption"
    a_photo.donor = a_donor
    a_donor.archive = remote_archive
    a_photo.year = 1923
    a_photo.save()
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Create")
    ct = ContentType.objects.get_for_model(models.Photo)
    rdd = models.LdId.objects.create(content_type=ct, ld_id='http://example.com/kf/activitypub/archives/an-archive/photos/1', object_id=a_photo.id)
    data=activitypub.ActivitySchema().dump({
        "actor": remote_archive,
        "object": a_photo,
        "type": "Update",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    })
    a_photo.caption = "new caption"
    a_photo.save()
    request = RequestFactory().post(
        "/kf/activitypub/service/inbox",
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        headers={
            "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
        data=json.dumps(data),
    )
    request.actor = remote_archive.actor
    Site.objects.all().update(domain='example2.net')
    resp = activitypub.service_inbox(request)
    assert resp.status_code == 200
    assert models.Photo.objects.all().exists()
    assert models.Photo.objects.all()[0].caption == 'old caption'




@pytest.mark.django_db
def test_updatecontacthandler(a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    a_donor.first_name = "fake"
    a_donor.last_name = "name"
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Create")
    a_donor.first_name = "first"
    a_donor.last_name = "Last"
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Update")
    assert models.Donor.objects.count() == 2
    assert models.Donor.objects.filter(archive=remote_archive)[0].first_name == "first"
    assert models.Donor.objects.filter(archive=remote_archive)[0].last_name == "Last"
    assert models.LdId.objects.exists()

@pytest.mark.django_db
def test_deletehandler(a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    a_donor.first_name = "fake"
    a_donor.last_name = "name"
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Create")
    ld_id = models.LdId.objects.all()[0]
    activitypub.DeleteObject().handle(
        archive=remote_archive,
        object={
            "type": "Contact",
            "href": ld_id.ld_id,
        },
        root_type="Delete"
    )
    assert models.Donor.objects.count() == 1
    assert not models.LdId.objects.exists()

@pytest.mark.django_db
def test_createcontacthandler(a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Create")
    assert models.Donor.objects.count() == 2
    assert models.LdId.objects.exists()
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_donor), root_type="Create")
    assert models.Donor.objects.count() == 2

def assertPhotosEqual(photo_a, photo_b):
    assert photo_b.year == photo_a.year
    assert photo_b.category.name == photo_a.category.name
    assert photo_b.category.slug == photo_a.category.slug
    assert photo_b.circa == photo_a.circa
    assert photo_b.is_published == photo_a.is_published
    assert photo_b.donor.first_name == photo_a.donor.first_name
    assert photo_a.original.url == photo_b.remote_image
    assert set(t.term for t in photo_b.terms.all()) == set(t.term for t in photo_a.terms.all())
    assert set(t.tag for t in photo_b.get_accepted_tags()) == set(t.tag for t in photo_a.get_accepted_tags())

@pytest.mark.django_db
def test_createimagehandler(a_photo, a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    a_photo.caption = "caption"
    a_photo.year = 1954
    a_photo.donor = a_donor
    a_photo.circa = True
    a_photo.is_published = True
    a_photo.terms.add(models.Term.objects.create(term="ExampleTerm"))
    models.PhotoTag.objects.create(photo=a_photo, tag=models.Tag.objects.create(tag="example"), accepted=True)
    activitypub.CreateContact().handle(archive=remote_archive, object=activitypub.Contact().dump(a_photo.donor), root_type="Create")
    Site.objects.all().update(domain='example2.net')
    activitypub.CreateImage().handle(archive=remote_archive, object=activitypub.Image().dump(a_photo), root_type="Create")
    assert models.Photo.objects.count() == 2
    saved = models.Photo.objects.get(archive=remote_archive)
    assert models.LdId.objects.count() == 2
    assertPhotosEqual(a_photo, saved)
    activitypub.CreateImage().handle(archive=remote_archive, object=activitypub.Image().dump(a_photo), root_type="Create")
    assert models.Photo.objects.count() == 2

@override_settings(KF_URL_SCHEME="http:")
@pytest.mark.django_db
def test_createimagehandler_unknown_donor(a_photo, a_donor):
    remote_archive = Archive.objects.create(type=Archive.ArchiveType.REMOTE, slug="an-archive", actor=models.RemoteActor.objects.create(profile="http://example.com/kf/activitypub/archives/an-archive", app_follows_actor=True))
    a_photo.caption = "caption"
    a_photo.donor = a_donor
    a_photo.archive = remote_archive
    a_donor.archive = remote_archive
    with mock.patch("requests.get") as mock_:
        mock_.return_value = mock.Mock(name="json")
        mock_.return_value.json.return_value = activitypub.Contact().dump(a_donor)
        Site.objects.all().update(domain='example2.net')
        activitypub.CreateImage().handle(archive=remote_archive, object=activitypub.Image().dump(a_photo), root_type="Create")
    mock_.assert_called_with(
        "http://example.com/kf/activitypub/archives/an-archive/contributors/1",
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
    )
    assert models.Photo.objects.count() == 2
    saved = models.Photo.objects.get(archive=remote_archive)
    assert models.LdId.objects.count() == 2
    assertPhotosEqual(a_photo, saved)
    activitypub.CreateImage().handle(archive=remote_archive, object=activitypub.Image().dump(a_photo), root_type="Create")
    assert models.Photo.objects.count() == 2

@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_donor_api(a_donor):
    client = Client()
    url = "/kf/activitypub/archives/{}/contributors/{}".format(a_donor.archive.slug, a_donor.id)
    resp = client.get(url)
    assert resp.status_code == 200
    donor = Contact().load(resp.json())
    assert a_donor.first_name == donor['firstName']
    assert a_donor.last_name == donor['lastName']

@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_photo_api(a_photo):
    a_photo.caption = "a caption"
    a_photo.year = 1920
    a_photo.save()
    client = Client()
    url = "/kf/activitypub/archives/{}/photos/{}".format(a_photo.archive.slug, a_photo.id)
    resp = client.get(url)
    assert resp.status_code == 200
    Site.objects.all().update(domain='example2.net')
    photo = Image().load(resp.json())
    assert photo['content'] == a_photo.caption

@pytest.mark.django_db
def test_signature_requires_correct_key_pair():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )

    invalid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    body = json.dumps(message)
    headers = SignatureHeaders(
        url=url,
        msg_body=body,
        host="example.com",
    )

    resp = client.post(
        url,
        data=body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=invalid_private_key, keyId="https://anotherinstance.com/activitypub/service"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401

@pytest.mark.django_db
def test_signature_requires_correct_key_pair():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )

    invalid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    body = json.dumps(message)
    headers = SignatureHeaders(
        url=url,
        msg_body=body,
        host="example.com",
    )

    resp = client.post(
        url,
        data=body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=invalid_private_key, keyId="https://anotherinstance.com/activitypub/service"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401

@pytest.mark.django_db
def test_signature_requires_correct_url_path():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )

    body = json.dumps(message)
    headers = SignatureHeaders(
        url="/some/other/path",
        msg_body=body,
        host="example.com",
    )

    resp = client.post(
        url,
        data=body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=valid_private_key, keyId="https://anotherinstance.com/activitypub/service"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401
@pytest.mark.django_db
def test_signature_requires_recent_date():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )

    body = json.dumps(message)
    headers = SignatureHeaders(
        url=url,
        msg_body=body,
        host="example.com",
        date=datetime(2024, 2, 1, 1, 1, 1, tzinfo=timezone.utc)
    )

    resp = client.post(
        url,
        data=body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=valid_private_key, keyId="https://anotherinstance.com/activitypub/service"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401

@pytest.mark.django_db
def test_signature_requires_correct_digest():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    )

    body = json.dumps(message)
    headers = SignatureHeaders(
        url=url,
        msg_body="{}",
        host="example.com",
    )

    resp = client.post(
        url,
        data=body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=valid_private_key, keyId="https://anotherinstance.com/activitypub/service"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401

#@pytest.mark.django_db
#def test_service_requires_correct_accept_header():
#    client = Client()
#    resp = client.get("/kf/activitypub/service")
#    assert resp.status_code == 406

@pytest.mark.django_db
def test_archive_followers_get_photo_create(an_archive, a_donor, a_category):
    actor = models.RemoteActor.objects.create(profile="https://anotherinstance.com/actor")
    an_archive.name = "an archive"
    an_archive.slug = "an-archive"
    an_archive.save()
    actor.archives_followed.add(an_archive)
    with mock.patch("requests.get") as mock_:
        mock_.return_value = mock.Mock(name="json")
        mock_.return_value.json.return_value = {"inbox": "https://anotherinstance.com/actor/inbox"}
        with mock.patch("requests.post") as post:
            photo = models.Photo.objects.create(
                donor=a_donor,
                archive=an_archive,
                is_published=True,
                original=SimpleUploadedFile("small.gif", small_gif, content_type="image/gif"),
                category=a_category,
            )
            mock_.assert_called_with("https://anotherinstance.com/actor")
            assert len(post.mock_calls) == 1
            assert post.mock_calls[0][1] == ('https://anotherinstance.com/actor/inbox',)
            data = json.loads(post.mock_calls[0][2]['data'])
            assert data['type'] == 'Create'

@pytest.mark.django_db
def test_service_has_valid_response():
    client = Client()
    url = "/kf/activitypub/service"
    resp = client.get(
        url,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    data = resp.json()
    assert data['inbox']
    assert data['outbox']
    assert data['id'].endswith(url)

@pytest.mark.django_db
def test_archive_actor_profile():
    client = Client()
    Archive.objects.create(slug="asdf")
    url = "/kf/activitypub/archives/asdf"
    resp = client.get(
        url,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
    )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    data = resp.json()
    assert data['inbox']
    assert data['outbox']
    assert data['id'].endswith(url)

@pytest.mark.django_db
def test_archive_inbox_follow_request():
    client = Client()
    Archive.objects.create(slug="asdf")
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Follow",
        "actor": "https://anotherinstance.com/kf/activitypub/service",
        "object": "https://example.com/kf/activitypub/archives/asdf",
    }
    url = "/kf/activitypub/archives/asdf/inbox"
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/kf/activitypub/service",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
        30,
    )
    msg_body = json.dumps(message)
    headers = SignatureHeaders(
        url=url,
        msg_body=msg_body,
        host="example.com",
    )
    resp = client.post(
        url,
        data=msg_body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(private_key=valid_private_key, keyId="https://anotherinstance.com/activitypub/archive/asdf"),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    assert FollowArchiveRequest.objects.exists()
    assert FollowArchiveRequest.objects.all()[0].request_body['id'] == 'https://anotherinstance.com/123'


@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_service_inbox_accept_request():
    client = Client()
    url = "/kf/activitypub/service/inbox"
    follow = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://example.com/kf/activitypub/service/outbox/321",
        "type": "Follow",
        "actor": "https://example.com/kf/activitypub/service",
        "object": "https://anotherinstance.com/kf/activitypub/archives/asdf",
    }
    message = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": "https://anotherinstance.com/123",
        "type": "Accept",
        "actor": "https://anotherinstance.com/activitypub/archive/asdf",
        "object": follow,
    }
    msg_body = json.dumps(message)

    OutboxActivity.objects.create(body=follow)
    valid_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    valid_public_key = valid_private_key.public_key()
    cache.set(
        "kronofoto:keyId:https://anotherinstance.com/activitypub/archive/asdf",
        valid_public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
        30,
    )
    headers = SignatureHeaders(
        url=url,
        msg_body=msg_body,
        host="example.com",
    )
    with mock.patch("requests.get") as mock_:
        mock_.return_value = mock.Mock(name="json")
        mock_.return_value.json.return_value = {"slug": "aslug", "name": "a detailed name"}
        resp = client.post(
            url,
            data=msg_body,
            headers={
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                "Signature": headers.signature(private_key=valid_private_key, keyId="https://anotherinstance.com/activitypub/archive/asdf"),
                "Host": headers.host,
                "Date": headers.date_format,
                "Digest": headers.digest,
            },
            content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    assert Archive.objects.filter(actor__profile="https://anotherinstance.com/activitypub/archive/asdf").exists()
