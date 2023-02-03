from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse
from ..forms import TagForm
from .basetemplate import BaseTemplateMixin
from ..models import Photo


class AddTagView(BaseTemplateMixin, LoginRequiredMixin, FormView):
    template_name = 'archive/add_tag.html'
    form_class = TagForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photo'] = self.photo
        context['tags'] = self.photo.get_accepted_tags(self.request.user)
        return context

    def dispatch(self, request, photo):
        self.photo = Photo.objects.get(id=photo)
        self.success_url = reverse('kronofoto:addtag', kwargs={'photo': self.photo.id})
        return super().dispatch(request)

    def form_valid(self, form):
        form.add_tag(self.photo, user=self.request.user)
        return super().form_valid(form)
