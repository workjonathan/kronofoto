from hypothesis.extra.django import from_model, register_field_strategy, TestCase, from_form
from django.test import Client, RequestFactory, SimpleTestCase
from hypothesis import given, strategies as st, note, settings as hsettings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle, initialize, consumes, precondition
from pytest import raises

from django.views.generic import TemplateView
from django.http import HttpResponse, QueryDict
from django import forms
from collections import defaultdict
from archive.views.multiform import MultiformView, StepForm


class Form1Invalid(forms.Form):
    f1 = forms.IntegerField(required=True, min_value=11, max_value=100)
class Form1(forms.Form):
    f1 = forms.IntegerField(required=True, min_value=1, max_value=10)
    @classmethod
    def get_invalid(self):
        return Form1Invalid

class Form2Invalid(forms.Form):
    f2 = forms.CharField(required=True, min_length=1, max_length=4)
class Form2(forms.Form):
    f2 = forms.CharField(required=True, min_length=5, max_length=10)
    @classmethod
    def get_invalid(self):
        return Form2Invalid

class Form3Invalid(forms.Form):
    pass
class Form3(forms.Form):
    f3 = forms.BooleanField(required=True)
    @classmethod
    def get_invalid(self):
        return Form3Invalid

class Form4Invalid(forms.Form):
    f4 = forms.IntegerField(required=True, min_value=100, max_value=110)
class Form4(forms.Form):
    f4 = forms.IntegerField(required=True, min_value=1, max_value=10)
    @classmethod
    def get_invalid(self):
        return Form4Invalid


class MultiformTestView(MultiformView):
    form_classes = [Form1, Form2, Form3, Form4]

class MultiformStateMachine(RuleBasedStateMachine):
    invalid_forms = Bundle("invalid_forms")
    valid_forms = Bundle("valid_forms")
    def __init__(self):
        super().__init__()
        self.client = Client()
        self.forms = {}
        self.submitted = {}
        self.submitted_valid = {}

    @rule()
    def get(self):
        resp = self.client.get('/test/multiform')
        assert resp.status_code == 200
        stepform = StepForm(data=resp.context['step_form'].initial)
        assert stepform.is_valid()
        assert stepform.cleaned_data['step'] == 0
        self.forms[stepform.cleaned_data['step']] = resp.context['form'].__class__
        self.submitted = {}
        self.submitted_valid = {}

    @precondition(lambda self: self.forms)
    @rule(target=invalid_forms, data=st.data())
    def create_invalid(self, data):
        step = data.draw(st.sampled_from(list(self.forms)))
        form = data.draw(from_form(self.forms[step].get_invalid()))
        assert form.is_valid()
        return (step, form)

    @precondition(lambda self: self.forms)
    @rule(target=valid_forms, data=st.data())
    def create_valid(self, data):
        step = data.draw(st.sampled_from(list(self.forms)))
        form = data.draw(from_form(self.forms[step]))
        assert form.is_valid()
        return (step, form)

    @rule(form=invalid_forms)
    def post_invalid(self, form):
        step, form = form
        data = form.data
        data['step'] = step
        resp = self.client.post('/test/multiform', data=data)
        assert resp.status_code == 200

        stepform2 = StepForm(data=resp.context['step_form'].initial)
        assert stepform2.is_valid()
        assert stepform2.cleaned_data['step'] == step
        form_data = resp.context['form'].initial or resp.context['form'].data
        assert not self.forms[step](data=form_data).is_valid()
        resp_form = self.forms[step].get_invalid()(data=form_data)
        assert resp_form.is_valid()
        self.submitted[step] = form
        self.submitted_valid[step] = False
        assert form.cleaned_data == resp_form.cleaned_data

    @rule(form=valid_forms)
    def post_valid(self, form):
        step, form = form
        self.submitted[step] = form
        self.submitted_valid[step] = True
        data = form.data
        data['step'] = step
        if step == 3 and len(self.submitted) == 4 and all(self.submitted_valid.values()):
            with raises(NotImplementedError):
                self.client.post('/test/multiform', data=data)
            self.submitted = {}
            self.submitted_valid = {}
        else:
            resp = self.client.post('/test/multiform', data=data)
            assert resp.status_code == 200
            stepform2 = StepForm(data=resp.context['step_form'].initial)
            assert stepform2.is_valid()
            assert stepform2.cleaned_data['step'] != step
            self.forms[stepform2.cleaned_data['step']] = resp.context['form'].__class__

            resp_form_class = self.forms[stepform2.cleaned_data['step']]
            form_data = resp.context['form'].initial or resp.context['form'].data
            resp_form = resp_form_class(data=form_data)
            if resp_form.is_valid():
                pass
            else:
                resp_form_class = resp_form_class.get_invalid()
                resp_form = resp_form_class(data=form_data)
            if resp_form.is_valid() and stepform2.cleaned_data['step'] in self.submitted:
                assert resp_form.cleaned_data == self.submitted[stepform2.cleaned_data['step']].cleaned_data



MultiformStateMachine.TestCase.settings = hsettings(max_examples = 50, stateful_step_count = 100, deadline=None)

class MultiformTest(TestCase, MultiformStateMachine.TestCase):
    "Note that this test runs in a TestCase without using transactions."
    "Since each run should have a unique session, this should be okay."
    "If there are other uses of database in this test, they will misbehave."
    pass
