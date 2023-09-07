from dataclasses import dataclass
from django.views.generic import TemplateView
from django import forms
from collections import defaultdict
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile

class StepForm(forms.Form):
    step = forms.IntegerField(widget=forms.HiddenInput)


@dataclass
class SessionDictionary:
    session_key: str
    session: "session"

    def get(self, key, default=None):
        return self.session[self.session_key].get(str(key), default)

    def set(self, key, value):
        self.session[self.session_key][str(key)] = value
        self.session.modified = True

    def clear(self):
        self.session[self.session_key] = {}
        self.session.modified = True

    def contains(self, key):
        return str(key) in self.session[self.session_key]

    def __len__(self):
        return len(self.session[self.session_key])

    def values(self):
        return self.session[self.session_key].values()


class MultiformView(TemplateView):
    initials = defaultdict(dict)
    session_store = "multiform_store"
    storage = FileSystemStorage(location="/tmp/kf_tmp")
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.data_store = SessionDictionary(session_key=self.get_session_data_store(), session=request.session)
        self.completed_form_store = SessionDictionary(session_key=self.get_session_completed_form_store(), session=request.session)
        self.file_store = SessionDictionary(session_key=self.get_session_files_store(), session=request.session)

    def get_session_files_store(self):
        return self.session_store + "_files"

    def get_session_data_store(self):
        return self.session_store + "_data"

    def get_session_completed_form_store(self):
        return self.session_store + "_form"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        form_class = self.form_classes[self.step]
        initial = self.data_store.get(self.step, None)
        if initial is None:
            form_kwargs = {"initial": self.initials[self.step]}
        else:
            form_kwargs = {"data": initial, "files": self.load_files(self.step)}
        context['form'] = form_class(**form_kwargs)
        context['step_form'] = StepForm(initial={'step': self.step})

        return context

    def get(self, *args, **kwargs):
        self.step = 0
        self.data_store.clear()
        self.file_store.clear()
        self.completed_form_store.clear()
        return super().get(*args, **kwargs)

    def save_files(self, step, files):
        file_data = {}
        for (field, data) in files.items():
            path = self.storage.save(data.name, data)
            file_data[field] = {
                "path": path,
                "name": data.name,
                "content_type": data.content_type,
                "size": data.size,
                "charset": data.charset,
            }
            data.open()
        self.file_store.set(step, file_data)

    def load_files(self, step):
        file_data = {}
        for (field, data) in self.file_store.get(step, {}).items():
            file_data[field] = UploadedFile(
                file=self.storage.open(data['path']),
                name=data['name'],
                content_type=data['content_type'],
                size=data['size'],
                charset=data['charset'],
            )
        return file_data

    def post(self, *args, **kwargs):
        stepform = StepForm(self.request.POST)
        self.step = 0
        if stepform.is_valid():
            self.step = stepform.cleaned_data['step']
            form = self.form_classes[self.step](self.request.POST, files=self.request.FILES or None)
            self.data_store.set(self.step, form.data)
            self.save_files(self.step, self.request.FILES)
            if form.is_valid():
                self.completed_form_store.set(self.step, form.data)
                accepted_step = self.step
                self.step = 0
                while self.step < accepted_step+1 and self.completed_form_store.get(self.step, None) is not None:
                    self.step += 1
                if self.step >= len(self.form_classes) and len(self.completed_form_store) == len(self.form_classes):
                    forms = [
                        cls(self.completed_form_store.get(i), self.load_files(i))
                        for (i, cls)
                        in enumerate(self.form_classes)
                    ]
                    for form in forms:
                        assert form.is_valid()
                    resp = self.forms_valid(forms)
                    self.data_store.clear()
                    self.completed_form_store.clear()
                    return resp
            else:
                self.completed_form_store.set(self.step, None)
            context = self.get_context_data()
            return self.render_to_response(context)

    def forms_valid(self, forms):
        raise NotImplementedError
