import pytest
from django.test import Client, RequestFactory
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, OutboxActivity, RemoteArchive
from fortepan_us.kronofoto.views.activitypub import decode_signature, decode_signature_headers
import json
from django.core.cache import cache
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from datetime import datetime, timezone
import base64
import hashlib

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
def test_validates_request():
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

    resp = client.post(
        url,
        data=json.dumps(message),
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": 'keyId="a",headers="a",signature="{}"'.format(base64.b64encode(b'a')),
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 401

def test_service_requires_correct_accept_header():
    client = Client()
    resp = client.get("/kf/activitypub/service")
    assert resp.status_code == 406

@pytest.mark.django_db
def test_service_has_valid_response():
    client = Client()
    url = "/kf/activitypub/service"
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
    url = "/kf/activitypub/archives/asdf/inbox"
    resp = client.post(
        url,
        data=json.dumps({
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "https://anotherinstance.com/123",
            "type": "Follow",
            "actor": "https://anotherinstance.com/kf/activitypub/service",
            "object": "https://example.com/kf/activitypub/archives/asdf",
        }),
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    assert FollowArchiveRequest.objects.exists()
    assert FollowArchiveRequest.objects.all()[0].request_body['id'] == 'https://anotherinstance.com/123'

from dataclasses import dataclass, field
from typing import Any

@dataclass
class SignatureHeaders:
    url: str
    msg_body: str
    host: str
    keyId: str
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verb: str = "post"

    @property
    def request_target(self) -> str:
        return f'{self.verb} {self.url}'

    @property
    def date_format(self) -> str:
        return self.date.strftime("%a, %d %b %Y %H:%M:%S %Z")

    @property
    def digest(self) -> str:
        digester = hashlib.sha256()
        digester.update(self.msg_body.encode('utf-8'))
        digest = base64.b64encode(digester.digest()).decode("utf-8")
        return f'SHA-256={digest}'

    @property
    def signed_headers(self) -> str:
        return "\n".join(
            f"{part}: {part_body}"
            for (part, part_body) in [
                ("(request-target)", self.request_target),
                ("host", self.host),
                ("date", self.date_format),
                ("digest", self.digest),
            ]
        )
    def signature(self, private_key: Any) -> str:
        signed_headers = self.signed_headers
        signature = private_key.sign(
            signed_headers.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256()
        )
        return 'keyId="{}",headers="(request-target) host date digest",signature="{}"'.format(self.keyId, base64.b64encode(signature).decode("utf-8"))


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
        keyId="https://anotherinstance.com/activitypub/archive/asdf"
    )
    resp = client.post(
        url,
        data=msg_body,
        headers={
            'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "Signature": headers.signature(valid_private_key),
            "Host": headers.host,
            "Date": headers.date_format,
            "Digest": headers.digest,
        },
        content_type='application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    )
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    assert RemoteArchive.objects.filter(actor__profile="https://anotherinstance.com/activitypub/archive/asdf").exists()
