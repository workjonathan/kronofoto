import pytest
import requests
from unittest import mock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, override_settings
from hypothesis import given, strategies as st, note
from hypothesis.extra.django import TestCase
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
from .util import photos, donors, archives, small_gif, a_photo, a_category, an_archive, a_donor
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType

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
@override_settings(KF_URL_SCHEME="http:")
def test_archive_get_or_create_by_profile_for_local_archive(an_archive):
    # When could this happen?
    with mock.patch('requests.get') as mock_:
        archive, created = models.Archive.objects.get_or_create_by_profile("http://example.com/kf/activitypub/archives/aslug")
        assert not created
        assert archive.id == an_archive.id
        mock_.assert_not_called()

@pytest.mark.django_db
def test_ldid_get_or_create_encounters_a_local_object(a_donor, an_archive):
    a_donor.archive = an_archive
    a_donor.save()
    with mock.patch('requests.get') as mock_:
        ldid, created = models.LdId.objects.get_or_create_ld_object("http://example.com/kf/activitypub/archives/aslug/contributors/1")
        assert not created
        assert a_donor.id == ldid.content_object.id
        mock_.assert_not_called()

@pytest.mark.django_db
def test_ldid_get_or_create_encounters_unknown_actor():
    with mock.patch('requests.get') as mock_:
        mock_.return_value = mock.Mock(name="json")
        mock_.return_value.json.side_effect = [
            {
                "id": "http://127.0.0.1:8000/kf/activitypub/archives/an-archive/contributors/1",
                "type": "Contact",
                "attributedTo": ["https://example.com/remotesite"],
                "firstName": "first",
                "lastName": "last",
            },
            {
                "id": "https://example.com/remotesite",
                "type": "Organization",
                "name": "OrgName",
                "slug": "an-archive",
            },
        ]
        models.LdId.objects.get_or_create_ld_object(ld_id="http://127.0.0.1:8000/kf/activitypub/archives/an-archive/contributors/1")

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
