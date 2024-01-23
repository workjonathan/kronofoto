from django.core.signing import Signer, BadSignature
from .models.photo import Photo, FixedResizer, FixedHeightResizer, ResizerBase, FixedWidthResizer
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from typing import Optional, Any, Dict, Union, List
from dataclasses import dataclass
from functools import cached_property
from .reverse import reverse

@dataclass
class ImageCacher:
    block1: int
    block2: int
    path: str
    sig: str
    width: Optional[int]
    height: Optional[int]

    def precache(self) -> bytes:
        Image.MAX_IMAGE_PIXELS = 195670000
        with default_storage.open(self.path) as infile:
            image = ImageOps.exif_transpose(Image.open(infile))
        w, h = image.size
        if self.width is not None and self.height is not None:
            resizer: ResizerBase = FixedResizer(width=self.width, height=self.height, original_height=h, original_width=w)
        elif self.height is not None:
            resizer = FixedHeightResizer(height=self.height, original_height=h, original_width=w)
        elif self.width is not None:
            resizer = FixedWidthResizer(width=self.width, original_height=h, original_width=w)
        img = resizer.resize(image=image)
        bytes = BytesIO()
        img.save(bytes, format="JPEG", quality=60)
        img_data = bytes.getvalue()
        name = "images/{}/{}/{}.jpg".format(self.block1, self.block2, self.sig)
        if not default_storage.exists(name):
            default_storage.save(
                name,
                ContentFile(img_data)
            )
        return img_data

@dataclass
class ImageSigner:
    id: int
    path: str
    width: Optional[int]=None
    height: Optional[int]=None

    @property
    def block1(self) -> int:
        return self.id & 255

    @property
    def block2(self) -> int:
        return (self.id >> 8) & 255

    @property
    def sig(self) -> str:
        return self.signed_object[1]

    @property
    def content(self) -> str:
        return self.signed_object[0]

    @cached_property
    def signed_object(self) -> List[str]:
        return self.signer.sign_object(self.profile_args).split(':')

    @cached_property
    def signer(self) -> Signer:
        return Signer(salt="{}/{}".format(self.block1, self.block2))

    @property
    def profile_args(self) -> Dict[str, Union[int, str]]:
        profile_args: Dict[str, Union[int, str]] = {"path": self.path}
        if self.width:
            profile_args['width'] = self.width
        if self.height:
            profile_args['height'] = self.height
        return profile_args

    @property
    def url(self) -> str:
        return "{}?i={}".format(
            reverse("kronofoto:resize-image", kwargs={'block1': self.block1, 'block2': self.block2, 'profile1': self.sig}), self.content
        )

    @property
    def cacher(self) -> ImageCacher:
        return ImageCacher(
            block1=self.block1, block2=self.block2, path=self.path, sig=self.sig, width=self.width, height=self.height
        )
