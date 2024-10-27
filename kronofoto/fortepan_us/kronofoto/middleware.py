from django.http import HttpRequest, HttpResponse
from typing import Callable
from django.urls import resolve
from django.utils.cache import patch_vary_headers
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List
import parsy # type: ignore
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import json
from fortepan_us.kronofoto.models import RemoteActor

@dataclass
class SignatureHeaders:
    url: str
    msg_body: str
    host: str
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verb: str = "post"
    date_format_str: ClassVar[str] = "%a, %d %b %Y %H:%M:%S %Z"


    @property
    def request_target(self) -> str:
        return f'{self.verb} {self.url}'

    @property
    def date_format(self) -> str:
        return self.date.strftime(self.date_format_str)

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

    def signature(self, *, private_key: Any, keyId: str) -> str:
        signed_headers = self.signed_headers
        signature = private_key.sign(
            signed_headers.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256()
        )
        return 'keyId="{}",headers="(request-target) host date digest",signature="{}"'.format(keyId, base64.b64encode(signature).decode("utf-8"))

# could be a decorator
class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if 'kronofoto' in resolve(request.path_info).app_names:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
            patch_vary_headers(response, ['embedded', 'constraint', 'hx-request']) # type: ignore
        return response

class OverrideVaryMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if hasattr(response, "override_vary"):
            response.headers['Vary'] = ""
            response.cookies.clear()
        return response

def decode_signature(signature: str) -> Dict[str, str]:
    quoted_string = parsy.string('"') >> parsy.regex(r'[^"]*') << parsy.string('"')
    key = parsy.regex(r'[^=]*')
    pair = parsy.seq(key << parsy.string("="), quoted_string)
    return dict(pair.sep_by(parsy.string(",")).parse(signature))

def decode_signature_headers(signature_headers: str) -> List[str]:
    return parsy.regex('[^ ]*').sep_by(parsy.whitespace).parse(signature_headers)

class ActorAuthenticationMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        signature_parts = decode_signature(request.headers.get("Signature", ""))
        body = request.body.decode("utf-8")
        if request.content_type == 'application/ld+json' and request.content_params and request.content_params.get("profile") == "https://www.w3.org/ns/activitystreams" and 'date' in request.headers:
            request_date = datetime.strptime(request.headers['date'], SignatureHeaders.date_format_str).replace(tzinfo=timezone.utc)
            if abs(request_date - datetime.now(timezone.utc)) <= timedelta(minutes=10):
                headers = SignatureHeaders(
                    url=request.path,
                    msg_body=body,
                    host=request.headers.get('host', ""),
                    date=request_date,
                    verb=(request.method or "get").lower(),
                )
                if headers.digest == request.headers.get("Digest", ""):
                    data = json.loads(body)
                    actor, _ = RemoteActor.objects.get_or_create(profile=data['actor'])
                    pubkey_str = actor.public_key()
                    if pubkey_str:
                        public_key = load_pem_public_key(pubkey_str)
                        if isinstance(public_key, RSAPublicKey):
                            try:
                                public_key.verify(
                                    base64.b64decode(signature_parts['signature']),
                                    headers.signed_headers.encode('utf-8'),
                                    padding.PSS(
                                        mgf=padding.MGF1(hashes.SHA256()),
                                        salt_length=padding.PSS.MAX_LENGTH,
                                    ),
                                    hashes.SHA256(),
                                )
                                setattr(request, "actor", actor)
                                setattr(request, "activity_message", data)
                            except InvalidSignature:
                                pass
        response = self.get_response(request)
        return response
