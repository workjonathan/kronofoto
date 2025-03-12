from typing import TypedDict, NewType, Literal, List, Union, Type, cast, Dict, Tuple, Optional, NamedTuple
from marshmallow import Schema, fields
from django.contrib.gis.geos import MultiPolygon, Point
from dataclasses import dataclass



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


class ActivitypubContact(ActivitypubObject):
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

@dataclass
class CategoryValue:
    slug: str
    name: str

@dataclass
class PhotoValue:
    id: str
    content: str
    category: CategoryValue
    circa: bool
    is_published: bool
    terms: List[str]
    tags: List[str]
    year: Optional[int]=None
    contributor: Optional[str] = None
    url: Optional[str] = None
    place: Optional[str] = None

@dataclass
class DonorValue:
    id: str
    attributedTo: List[str]
    name: Optional[str]
    firstName: str
    lastName: str

@dataclass
class PlaceValue:
    id: str
    name: str
    attributedTo: List[str]
    parent: Optional[LdIdUrl]
    placeType: str
    fullName: str
    geom: Optional[Union[Point, MultiPolygon]]

@dataclass
class DeleteValue:
    id: str
    actor: str
    object: str

@dataclass
class CreateValue:
    id: str
    actor: str
    object: Union[PhotoValue, DonorValue, PlaceValue]

@dataclass
class UpdateValue:
    id: str
    actor: str
    object: Union[PhotoValue, DonorValue, PlaceValue]

@dataclass
class FollowValue:
    id: str
    actor: str
    object: str

@dataclass
class AcceptValue:
    id: str
    actor: str
    object: FollowValue

class ActivitypubLocation(ActivitypubObject, total=False):
    name: str
    parent: Optional[LdIdUrl]
    type: Literal["Location"]
    geom: Union[None, Point, MultiPolygon]
    place_type: str


ActivitypubValue = Union[DeleteValue, CreateValue, UpdateValue, FollowValue, AcceptValue]
ActivitypubData = Union[ActivitypubImage, ActivitypubContact]

class Activity(TypedDict):
    actor: LdIdUrl
    object: Union[ActivitypubData, "ActivityTypes"]

class FollowActivity(Activity):
    type: Literal['Follow']

class AcceptActivity(Activity):
    type: Literal['Accept']

ActivityTypes = Union[FollowActivity, AcceptActivity]
