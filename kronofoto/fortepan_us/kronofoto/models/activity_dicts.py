from typing import TypedDict, NewType, Literal, List, Union, Type, cast
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
        "_context": str,
        "id": LdIdUrl,
        #"type": str,
        "attributedTo": List[LdIdUrl],
        "url": Url,
        'content': str,
    },
    total=False,
)

class ActivitypubContact(ActivitypubObject, total=False):
    type: Literal["Contact"]
    name: str
    firstName: str
    lastName: str

def get_field(name: str, type: Type) -> fields.Field:
    if type == str:
        return fields.Str()
    elif type == bool:
        return fields.Boolean()
    elif type == int:
        return fields.Integer()
    elif type == Literal["Contact"]:
        return fields.Constant("Contact")
    elif type == Literal["Image"]:
        return fields.Constant("Image")
    elif type == LdIdUrl:
        return fields.Url(relative=True)
    elif type == List[str]:
        return fields.List(fields.Str())
    elif type == List[LdIdUrl]:
        return fields.List(fields.Url())
    elif type == Url:
        return fields.Url(relative=True)
    elif type == ActivitypubCategory:
        return fields.Nested(Schema.from_dict({
            name: get_field(name, type) for (name, type) in type.__annotations__.items()
        }))
    raise NotImplementedError(name, type)

ActivitypubContactSchema = Schema.from_dict({
    name: get_field(name, type) for (name, type) in ActivitypubContact.__annotations__.items()
})

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

ActivitypubImageSchema = Schema.from_dict({
    name: get_field(name, type) for (name, type) in ActivitypubImage.__annotations__.items()
})

ActivitypubData = Union[ActivitypubImage, ActivitypubContact]
