from typing import TypedDict, NewType, Literal, List, Union, Type, cast, Dict
from marshmallow import Schema, fields


Url = NewType("Url", str)


def str_to_url(s: str) -> Url:
    return cast(Url, s)


LdIdUrl = NewType("LdIdUrl", Url)


def str_to_ldidurl(s: str) -> LdIdUrl:
    return cast(LdIdUrl, s)


ActivitypubCategory = TypedDict(
    "ActivitypubCategory",
    {
        "slug": str,
        "name": str,
    },
    total=True,
)

ActivitypubObject = TypedDict(
    "ActivitypubObject",
    {
        "@context": str,
        "id": LdIdUrl,
        # "type": str,
        "attributedTo": List[LdIdUrl],
        "url": Url,
        "content": str,
    },
    total=False,
)


class ArchiveDict(ActivitypubObject, total=False):
    type: Literal["Organization"]
    name: str
    slug: str
    publicKey: Dict[str, str]

    inbox: Url
    outbox: Url
    contributors: Url
    photos: Url
    following: Url
    followers: Url


class ActivitypubContact(ActivitypubObject, total=False):
    type: Literal["Contact"]
    name: str
    firstName: str
    lastName: str


class ActivitypubImage(ActivitypubObject, total=False):
    category: ActivitypubCategory
    type: Literal["Image"]
    year: int
    circa: bool
    is_published: bool
    contributor: LdIdUrl
    terms: List[str]
    tags: List[str]
    place: LdIdUrl

class ActivitypubLocation(ActivitypubObject, total=False):
    name: str
    parent: LdIdUrl
    type: Literal["Location"]
    geom: List[List[List[List[float]]]]


ActivitypubData = Union[ActivitypubImage, ActivitypubContact]
