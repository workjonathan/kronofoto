from django.http import HttpResponse, HttpRequest
from django.core.signing import Signer, BadSignature
from typing import Optional, Any, Dict, Union, List, Tuple
from dataclasses import dataclass
from fortepan_us.kronofoto.imageutil import ImageCacher
from django.views.decorators.cache import cache_control
from fortepan_us.kronofoto.decorators import strip_cookies

@cache_control(max_age=60*60, public=True)
def resize_image(request: HttpRequest, block1: int, block2: int, profile1: str) -> HttpResponse:
    signer = Signer(salt=f"{block1}/{block2}")
    spec = request.GET.get('i')
    profile = f"{spec}:{profile1}"
    try:
        unsigned = signer.unsign_object(profile)
        try:
            path: Union[str, Tuple[int, str]] = unsigned[0]
            width = unsigned[1]
            height = unsigned[2]
        except:
            return HttpResponse("Not found", status=404)
        cacher = ImageCacher(
            block1=block1,
            block2=block2,
            path=path,
            sig=profile1,
            width=width,
            height=height,
        )
        resp = HttpResponse(cacher.precache(), content_type="image/jpeg")
        setattr(resp, 'override_vary', True)
        return resp
    except BadSignature:
        return HttpResponse("Not found", status=404)
