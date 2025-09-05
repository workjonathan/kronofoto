from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from typing import Callable, Union, Optional, Dict, Any
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
import logging
import json
from fortepan_us.kronofoto.signed_requests import SignatureHeaders
from fortepan_us.kronofoto import models

logger = logging.getLogger(__name__)

class AnonymizerProtectionMiddleware:
    unsafe_cookies = ['csrftoken', 'sessionid']
    anonymize_paths = ['gridview', 'photoview']
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        resolve_match = resolve(request.path_info)
        anonymized = False
        if resolve_match.url_name in self.anonymize_paths and 'kronofoto' in resolve_match.app_names and 'collection:' not in request.GET.get('query', ""):
            for cookie in list(request.COOKIES):
                if cookie.lower() != 'django_language':
                    del request.COOKIES[cookie]
            anonymized = True
        setattr(request, "anonymized", anonymized)
        response = self.get_response(request)
        if anonymized:
            for cookie in list(response.cookies):
                if cookie.lower() in self.unsafe_cookies:
                    logger.warning("Removing unsafe cookie %s from %s response", cookie, request.path)
                    del response.cookies[cookie]
                return response
        return response


# could be a decorator
class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        resolve_match = resolve(request.path_info)
        if 'kronofoto' in resolve_match.app_names:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger'
            #patch_vary_headers(response, ['embedded', 'constraint', 'hx-request', 'hx-target']) # type: ignore
            hxtriggers = response.headers.get('Hx-Trigger', None)
            if hxtriggers:
                hxtriggersdict = json.loads(hxtriggers)
            else:
                hxtriggersdict = {}
            if hxtriggersdict:
                response.headers['Hx-Trigger'] = json.dumps(hxtriggersdict)
        return response

class OverrideVaryMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if hasattr(response, "override_vary"):
            del response.headers['Vary']
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
        from fortepan_us.kronofoto.models import RemoteActor
        signature_parts = decode_signature(request.headers.get("Signature", ""))
        if request.content_type == 'application/ld+json' and request.content_params and request.content_params.get("profile") == "https://www.w3.org/ns/activitystreams" and 'date' in request.headers:
            body = request.body.decode("utf-8")
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
