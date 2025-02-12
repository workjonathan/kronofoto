from django import template
from django.http import QueryDict
from django.core.signing import Signer
from django.http import HttpRequest
from fortepan_us.kronofoto.reverse import reverse
import markdown as md # type: ignore
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from fortepan_us.kronofoto.models import Photo, Card, Collection, PhotoCard, Figure, Exhibit
from fortepan_us.kronofoto.models.photo import LabelProtocol
from fortepan_us.kronofoto.imageutil import ImageSigner
from typing import Union, Dict, Any, Union, Optional, Tuple, List, Set, TypedDict
from django.template.defaultfilters import linebreaksbr, linebreaks_filter
from django.contrib.auth.models import User
from django.db.models import QuerySet, Q
from django.db.models.functions import Lower
import json
import uuid
from django import forms
from lxml import etree, html

register = template.Library()

@register.filter
def with_parent(figure: Figure, parent: str) -> Tuple[Figure, str]:
    return figure, parent
@register.filter
def figure_form(figure_parent: Tuple[Figure, str], photos: QuerySet[Photo]) -> forms.Form:
    figure, parent = figure_parent
    from ..forms.card import FigureForm
    form = FigureForm(prefix=str(uuid.uuid4()), initial={"parent": parent, 'card_type': 'figure'}, instance=figure)
    assert hasattr(form.fields['photo'], 'queryset')
    form.fields['photo'].queryset = photos
    return form

@register.filter
def all_tags_with(photo: Photo, user: Optional[User]=None) -> List[LabelProtocol]:
    return photo.get_all_tags(user=user)

@register.filter
def describe(object: Photo, user: Optional[User]=None) -> Set[str]:
    return object.describe(user)

@register.inclusion_tag('kronofoto/components/page-links.html', takes_context=False)
def page_links(formatter: Any, page_obj: Any, target: Any=None) -> Dict[str, Any]:
    links = [{'label': label} for label in ['First', 'Previous', 'Next', 'Last']]
    if page_obj.has_previous():
        links[0]['url'] = formatter.page_url(1)
        links[0]['target'] = target
        links[1]['url'] = formatter.page_url(page_obj.previous_page_number())
        links[1]['target'] = target
    if page_obj.has_next():
        links[2]['url'] = formatter.page_url(page_obj.next_page_number())
        links[2]['target'] = target
        links[3]['url'] = formatter.page_url(page_obj.paginator.num_pages)
        links[3]['target'] = target
    return dict(
        links=links,
        page_obj=page_obj
    )

@register.simple_tag(takes_context=False)
def image_url(*, id: int, path: str, width: Optional[int]=None, height: Optional[int]=None) -> str:
    return ImageSigner(id=id, path=path, width=width, height=height).url

def count_photos() -> int:
    return Photo.objects.filter(is_published=True).count()

@register.simple_tag(takes_context=False)
def photo_count() -> Optional[Any]:
    return cache.get_or_set("photo_count", count_photos)

@register.filter(is_safe=True)
@stringfilter
def markdown(text: str, extension: Optional[str]=None) -> str:
    # disable ParagraphProcessor?
    from .urlify import URLifyExtension
    extensions : List[Union[str, URLifyExtension]] = []
    extensions.append(URLifyExtension())
    if extension:
        extensions.append(extension)
    return mark_safe(md.markdown(escape(text), output_format="html", extensions=extensions))

@register.simple_tag(takes_context=False)
def thumb_left(*, index: int, offset: int, width: int) -> int:
    return index * width + offset


@register.inclusion_tag('kronofoto/components/thumbnails.html', takes_context=False)
def thumbnails(*, object_list: List[Photo], positioning: Optional[Dict[str, Any]], url_kwargs: Optional[Dict[str, Any]], get_params: Optional[QueryDict]) -> Dict[str, Any]:
    return  {
        "object_list": object_list,
        "positioning": positioning,
        "url_kwargs": url_kwargs,
        "get_params": get_params,
    }

class UserContentListContext(TypedDict, total=False):
    request_user: User
    profile_user: User
    form: Union[forms.Form, forms.ModelForm]
    section_id: str
    section_name: str
    form_template: str
    section_description: str
    object_list: Union[QuerySet["Exhibit"], QuerySet['Collection']]

@register.inclusion_tag("kronofoto/components/user-content-section.html", takes_context=False)
def collections(user: User, profile_user: User, form: Union[forms.ModelForm, forms.Form]) -> UserContentListContext:
    context: UserContentListContext = {
        'request_user': user,
        'profile_user': profile_user,
        "form": form,
        "section_id":"my-lists",
        "section_name": "My FotoAlbums",
        "form_template": "kronofoto/components/forms/collection-create.html",
        "section_description": "A FotoAlbum is a collection of Fortepan photos organized by a customizable theme. You can share and embed any FotoAlbum, and use a FotoAlbum to create a FotoStory.",
    }

    filter_kwargs = {}
    if user.id != profile_user.id:
        filter_kwargs['visibility'] = "PU"
    context['object_list'] = Collection.objects.by_user(user=profile_user, **filter_kwargs)
    return context



@register.inclusion_tag("kronofoto/components/user-content-section.html", takes_context=False)
def exhibits(user: User, profile_user: User, form: forms.Form) -> UserContentListContext:
    context : UserContentListContext = {
        'request_user': user,
        'profile_user': profile_user,
        "form": form,
        "section_id": "my-exhibits",
        "section_name": "My FotoStories",
        "form_template": "kronofoto/components/forms/exhibit-create.html",
        "section_description": "A FotoStory is a digital exhibit built with Fortepan photos; build a FotoStory with a combination of text + image content blocks. You can share and embed any FotoStory.",
    }
    context['object_list'] = Exhibit.objects.filter(owner=profile_user)
    return context

def rewrite_tree(tree: etree._Element) -> etree._Element:
    newTree = etree.Element(tree.tag)
    newTree.text = tree.text
    newTree.tail = tree.tail
    count = len(tree)
    for i, child in enumerate(tree):
        if child.tag != "p":
            newTree.append(rewrite_tree(child))
        else:
            if i != 0 or newTree.text:
                br = etree.Element("br")
                br.tail = child.text
                newTree.append(br)
            else:
                newTree.text = child.text
            for pchild in child:
                newTree.append(rewrite_tree(pchild))
            if i != count - 1 or child.tail:
                br = etree.Element("br")
                br.tail = child.tail
                newTree.append(br)
    return newTree


@register.filter
@stringfilter
def p_to_br(value: str) -> str:
    """Convert html string consisting of a list of <p> tags to one element separated by <br> pairs."""
    print(f"{value=}")
    try:
        tree = html.fromstring(value)
    except Exception as e:
        return value
    rewritten = rewrite_tree(tree)
    nodes = []
    if rewritten.text:
        nodes.append(rewritten.text)
    nodes += [etree.tostring(child).decode('utf-8') for child in rewritten]
    if rewritten.tail:
        nodes.append(rewritten.tail)
    return mark_safe("".join(nodes))
