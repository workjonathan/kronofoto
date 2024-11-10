import requests
import hashlib
from datetime import datetime, timezone, timedelta
import base64
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from urllib.parse import urlparse

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

def post(url: str, *, data: str="", keyId: str, private_key: rsa.RSAPrivateKey, headers: Optional[Dict[str, str]]=None) -> requests.Response:
    headers = headers or {}
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path += "?{}".format(parsed.query)
    if parsed.fragment:
        path += "#{}".format(parsed.fragment)
    sigheaders = SignatureHeaders(
        url=path,
        msg_body=data,
        host=parsed.netloc
    )
    headers['Host'] = sigheaders.host
    headers['Date'] = sigheaders.date_format
    headers['Digest'] = sigheaders.digest
    headers['Signature'] = sigheaders.signature(private_key=private_key, keyId=keyId)
    return requests.post(url, data=data, headers=headers)
