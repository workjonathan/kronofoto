import pytest
import requests
from unittest import mock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, override_settings
from hypothesis import given, strategies as st, note
from hypothesis.extra.django import TestCase
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, OutboxActivity, RemoteArchive
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
def test_receiving_a_donor_create_creates_a_donor():
    remote_archive = RemoteArchive.objects.create(slug="an-archive", actor=models.RemoteActor.objects.create(profile="https://example.com/actor"))
    request = RequestFactory().post("/kf/activitypub/service/inbox")
    request.actor = remote_archive
    resp = activitypub.service_inbox(request)
    assert resp.status_code == 200



@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_donor_api(a_donor):
    client = Client()
    url = "/kf/activitypub/archives/{}/contributors/{}".format(a_donor.archive.slug, a_donor.id)
    resp = client.get(url)
    assert resp.status_code == 200
    donor = Contact().load(resp.json())
    assert a_donor.id == donor.id
    assert a_donor.first_name == donor.first_name
    assert a_donor.last_name == donor.last_name

@pytest.mark.django_db
@override_settings(KF_URL_SCHEME="http:")
def test_photo_api(a_photo):
    a_photo.caption = "a caption"
    a_photo.save()
    client = Client()
    url = "/kf/activitypub/archives/{}/photos/{}".format(a_photo.archive.slug, a_photo.id)
    resp = client.get(url)
    assert resp.status_code == 200
    Site.objects.all().update(domain='example2.net')
    photo = Image().load(resp.json())
    assert photo.caption == a_photo.caption

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

def test_service_requires_correct_accept_header():
    client = Client()
    resp = client.get("/kf/activitypub/service")
    assert resp.status_code == 406

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
    assert RemoteArchive.objects.filter(actor__profile="https://anotherinstance.com/activitypub/archive/asdf").exists()
