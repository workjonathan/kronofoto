from django.urls import path, include, URLPattern, URLResolver
from django.shortcuts import get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from fortepan_us.kronofoto.auth.forms import AuthenticationForm
from fortepan_us.kronofoto import models
import typing

def login_form(request: HttpRequest) -> TemplateResponse:
    form = AuthenticationForm(request)
    form.fields['username'].widget.attrs['placeholder'] = 'Email'
    form.fields['password'].widget.attrs['placeholder'] = 'Password'
    return TemplateResponse(
        request=request,
        context={"form": form, 'user': request.user, 'request': request},
        template="kronofoto/components/login.html",
    )

def tag_form(request: HttpRequest, *, photo: int) -> TemplateResponse:
    return TemplateResponse(
        request=request,
        context={'photo': photo },
        template="kronofoto/components/forms/tag-photo.html",
    )

def edit_link(request: HttpRequest, *, photo: int) -> TemplateResponse:
    object = get_object_or_404(models.Photo.objects.all(), id=photo)
    return TemplateResponse(
        request=request,
        context={"photo": object},
        template="kronofoto/components/a/edit-link.html",
    )

app_name = "auth-forms"
urlpatterns : typing.List[typing.Union[URLPattern, URLResolver]] = [
    path("/login", login_form, name="login"),
    path("/tag-photo/<int:photo>", tag_form, name="tag-photo"),
    path("/edit-photo-link/<int:photo>", edit_link, name="edit-perm-check"),

]
