from django.views.generic import FormView
from django.contrib.sites.models import Site
from ..forms import WebComponentForm, SearchForm
from .basetemplate import BasePermissiveCORSMixin
from ..reverse import reverse
from ..search.parser import NoExpression

class WebComponentPopupView(BasePermissiveCORSMixin, FormView):
    template_name = 'archive/web-component.html'
    form_class = WebComponentForm
    def get_initial(self):
        return {'page': 'random'}

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        form = context['form']
        searchForm = SearchForm(self.request.GET)
        if searchForm.is_valid():
            try:
                expression = str(searchForm.as_expression())
            except NoExpression:
                expression = None
        context['expression'] = expression
        context['site'] = Site.objects.get_current().domain
        kwargs = self.kwargs.copy()
        kwargs.pop('photo')
        this_photo = reverse('kronofoto:photoview', kwargs=self.kwargs)
        choices = dict(WebComponentForm.CHOICES)
        if not form.is_valid() or form.cleaned_data['page'] == 'random':
            name = choices['random']
            src = reverse('kronofoto:random-image', kwargs=kwargs)
        elif form.cleaned_data['page'] == 'results':
            name = choices['results']
            src = reverse('kronofoto:gridview', kwargs=kwargs)
        else:
            name = choices[form.cleaned_data['page']]
            src = this_photo
        context['src'] = src
        context['name'] = name
        context['params'] = self.request.GET.copy()
        context['this_photo'] = this_photo
        if 'page' in context['params']:
            context['params'].pop('page')
        return context


        return context
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'page' in self.request.GET:
            kwargs.update({'data': self.request.GET})
        return kwargs
