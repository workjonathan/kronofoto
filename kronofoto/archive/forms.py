from django import forms
from .models import Tag

class TagForm(forms.Form):
    tag = forms.CharField()

    def add_tag(self, photo):
        tag, _ = Tag.objects.get_or_create(tag=self.cleaned_data['tag'])
        if not photo.tags.filter(id=tag.id).exists():
            photo.proposed_tags.add(tag)


