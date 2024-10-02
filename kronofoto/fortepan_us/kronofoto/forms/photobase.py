from django import forms
from typing import Any, Optional, List, Tuple, Union
from fortepan_us.kronofoto.models import Category, Term, Archive
from fortepan_us.kronofoto.models.category import ValidCategory
from fortepan_us.kronofoto.models.photo import Photo, Submission
from django.db.models import QuerySet

class PhotoBaseForm(forms.ModelForm):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        termsfield = self.fields.get('terms')
        instance : Optional[Photo] = kwargs.get('instance')
        if termsfield and hasattr(termsfield, 'choices'):
            termsfield.choices = self.get_term_choices(self.get_terms(instance))
        categoryfield = self.fields.get('category')
        if categoryfield and hasattr(categoryfield, 'choices'):
            categoryfield.choices = self.get_category_choices(self.get_categories(instance))

    def get_term_choices(self, queryset: QuerySet) -> Union[List[Tuple[Optional[str], List[Tuple[int, Term]]]], List[Tuple[Optional[str], List[Tuple[int, str]]]], List[Tuple[Optional[int], str]]]:
        choices: List[Tuple[Optional[int], str]] = list(queryset.values_list("id", "term"))
        choices.insert(0, (None, "---------"))
        return choices

    def get_category_choices(self, queryset: QuerySet) -> List[Tuple[Optional[int], str]]:
        choices: List[Tuple[Optional[int], str]] = list(queryset.values_list("id", "name"))
        choices.insert(0, (None, "---------"))
        return choices

    def get_categories(self, instance: Optional[Photo]=None) -> QuerySet[Category]:
        if not instance:
            return Category.objects.none()
        else:
            return instance.archive.categories.all()

    def get_terms(self, instance: Optional[Photo]) -> QuerySet[Term]:
        if not instance:
            return Term.objects.none()
        else:
            try:
                return ValidCategory.objects.get(archive=instance.archive, category=instance.category).terms.order_by('term')
            except:
                return Term.objects.none()

class ArchiveSubmissionForm(PhotoBaseForm):
    def __init__(self, *args: Any, **kwargs: Any):
        self.archive = kwargs.pop('force_archive', None)
        super().__init__(*args, **kwargs)

    def get_categories(self, instance: Optional[Photo]=None) -> QuerySet[Category]:
        return self.archive.categories.all()

    class Meta:
        model = Submission
        exclude : List[str] = ['state', 'city', 'county', 'country', 'address']

class SubmissionForm(PhotoBaseForm):
    class Meta:
        model = Submission
        exclude : List[str] = ['state', 'city', 'county', 'country', 'address']

class PhotoForm(PhotoBaseForm):
    class Meta:
        model = Photo
        exclude : List[str] = []
