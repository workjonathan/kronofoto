from django.views.generic import FormView
from django.contrib.sites.models import Site
from fortepan_us.kronofoto.forms import WebComponentForm, SearchForm
from fortepan_us.kronofoto.reverse import reverse
from fortepan_us.kronofoto.search.parser import NoExpression
from typing import Any, Dict, List, Union, Optional

class WebComponentPopupView(FormView):
    template_name = 'kronofoto/components/popups/web-component.html'
    form_class = WebComponentForm
    def get_initial(self) -> Dict[str, Any]:
        return {'page': 'random'}

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        form = context['form']
        searchForm = SearchForm(self.request.GET)
        if searchForm.is_valid():
            expression = searchForm.cleaned_data['expr']
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

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if 'page' in self.request.GET:
            kwargs.update({'data': self.request.GET})
        return kwargs
