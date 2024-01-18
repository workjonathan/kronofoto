from django.http import HttpResponse, HttpRequest
from django.core.signing import Signer, BadSignature
from ..models.photo import Photo, FixedResizer, FixedHeightResizer, ResizerBase, FixedWidthResizer
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def resize_image(request: HttpRequest, block1: int, block2: int, profile1: str, profile2: str) -> HttpResponse:
    signer = Signer(salt=f"{block1}/{block2}")
    profile = f"{profile1}:{profile2}"
    try:
        decoded = signer.unsign_object(profile)
        Image.MAX_IMAGE_PIXELS = 195670000
        with default_storage.open(decoded['path']) as infile:
            image = ImageOps.exif_transpose(Image.open(infile))
        w, h = image.size
        if 'width' in decoded and 'height' in decoded:
            resizer: ResizerBase = FixedResizer(width=decoded['width'], height=decoded['height'], original_height=h, original_width=w)
        elif 'height' in decoded:
            resizer = FixedHeightResizer(height=decoded['height'], original_height=h, original_width=w)
        elif 'width' in decoded:
            resizer = FixedWidthResizer(width=decoded['width'], original_height=h, original_width=w)
        img = resizer.resize(image=image)
        bytes = BytesIO()
        img.save(bytes, format="JPEG", quality=60)
        content = bytes.getvalue()
        name = "images/{}/{}/{}/{}.jpg".format(block1, block2, profile1, profile2)
        if not default_storage.exists(name):
            default_storage.save(
                name,
                ContentFile(content)
            )
        return HttpResponse(content, content_type="image/jpeg")
    except BadSignature:
        return HttpResponse("Not found", status=404)
