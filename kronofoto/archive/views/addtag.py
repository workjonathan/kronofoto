from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404
from ..reverse import reverse
from ..forms import TagForm
from .basetemplate import BaseTemplateMixin
from ..models import Photo
from django.http import HttpRequest, HttpResponse, QueryDict
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_exempt


#class AddTagView(BaseTemplateMixin, LoginRequiredMixin, FormView):
#    template_name = 'archive/add_tag.html'
#    form_class = TagForm
#    success_url = '/'
#
#    def get_context_data(self, **kwargs):
#        context = super().get_context_data(**kwargs)
#        context['photo'] = self.photo
#        context['tags'] = self.photo.get_accepted_tags(self.request.user)
#        return context
#
#    def dispatch(self, request, photo, **kwargs):
#        self.photo = get_object_or_404(Photo.objects.all(), id=photo)
#        self.success_url = reverse('kronofoto:addtag', kwargs=dict(**self.url_kwargs, **{'photo': self.photo.id}))
#        if request.GET:
#            self.success_url += '?' + request.GET.urlencode()
#        return super().dispatch(request, **kwargs)
#
#    def form_valid(self, form):
#        form.add_tag(self.photo, user=self.request.user)
#        return super().form_valid(form)


def tags_view(request: HttpRequest, photo: int) -> HttpResponse:
    object = get_object_or_404(Photo.objects.all(), id=photo)
    if request.method and request.method.lower() == 'put':
        if request.user.is_anonymous:
            raise PermissionDenied
        put_data = QueryDict(request.body)
        form = TagForm(data=put_data)
        if form.is_valid():
            form.add_tag(object, user=request.user)
    return TemplateResponse(
        request,
        "archive/snippets/tags.html",
        {"tags": object.get_all_tags(user=request.user)}
    )
