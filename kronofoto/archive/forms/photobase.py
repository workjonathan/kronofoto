from django import forms
from typing import Any, Optional, List
from ..models import Category, Term, Archive
from ..models.category import ValidCategory
from ..models.photo import Photo, Submission
from django.db.models import QuerySet

class PhotoBaseForm(forms.ModelForm):
    def __init__(self, *args: Any, **kwargs: Any):
        force_archive = kwargs.pop('force_archive', None)
        super().__init__(*args, **kwargs)
        instance : Optional[Photo] = kwargs.get('instance')
        categoryfield = self.fields['category']
        if hasattr(categoryfield, 'choices'):
            categoryfield.choices = list(self.get_categories(instance, archive=force_archive).values_list("id", "name"))
            categoryfield.choices.insert(0, (None, "---------"))

    def get_categories(self, instance: Optional[Photo]=None, archive: Optional[Archive]=None) -> QuerySet[Category]:
        if not archive and instance:
            archive = instance.archive
        if not archive:
            return Category.objects.none()
        return archive.categories.all()

class SubmissionForm(PhotoBaseForm):
    class Meta:
        model = Submission
        exclude : List[str] = []

class PhotoForm(PhotoBaseForm):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        termsfield = self.fields['terms']
        instance : Optional[Photo] = kwargs.get('instance')
        if hasattr(termsfield, 'choices'):
            termsfield.choices = list(self.get_terms(instance).values_list('id', 'term'))
            termsfield.choices.insert(0, (None, "---------"))

    def get_terms(self, instance: Optional[Photo]) -> QuerySet[Term]:
        if not instance:
            return Term.objects.none()
        try:
            return ValidCategory.objects.get(archive=instance.archive, category=instance.category).terms.order_by('term')
        except:
            return Term.objects.none()

    class Meta:
        model = Photo
        exclude : List[str] = []
