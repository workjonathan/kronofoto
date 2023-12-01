from django.db.models import Q, F, Value, Case, When, IntegerField, Sum, FloatField, BooleanField, Value
from django.db.models.functions import Cast, Length, Lower, Replace, Greatest, Least, StrIndex
from django.db.models import Subquery, Exists, OuterRef
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from functools import cached_property
from .. import models
from dataclasses import dataclass
from typing import Any

from functools import reduce
import operator
import re

SPLITTER = re.compile(' |`|\'|"')

STOPWORDS = {
    'yourselves', "shan't", "we'll", 'ourselves', 'out', 'who', 'not', 'off',
    'she', 'these', 'theirs', 'between', 'the', "i'm", 'no', "there's", 'are',
    "that's", 'doing', 'themselves', 'to', 'what', 'all', 'and', 'be', "can't",
    'ours', 'under', 'there', 'does', 'his', 'he', 'some', 'me', "i'd", 'but',
    'up', "we're", 'down', 'herself', 'too', 'having', 'after', 'above', 'its',
    'their', "she'd", 'further', "aren't", 'again', 'her', 'only', "when's",
    'own', 'those', 'than', 'when', 'myself', 'by', 'was', 'has', 'at', "she's",
    'below', 'against', 'would', 'more', 'on', 'once', 'cannot', 'that',
    "don't", "couldn't", 'your', 'most', 'any', "what's", "he's", 'whom',
    'ought', "let's", "why's", 'i', 'this', 'it', "how's", "where's", "you'll",
    'few', "he'll", "wasn't", "haven't", 'a', 'because', 'do', "isn't", 'were',
    'being', 'could', 'until', 'over', 'why', "shouldn't", 'we', 'in', 'with',
    'same', 'him', 'so', 'an', 'very', 'them', 'am', 'you', 'itself', "i've",
    "she'll", "you've", 'my', "i'll", 'through', 'such', 'did', 'hers',
    "hasn't", "we'd", 'himself', 'before', 'for', "wouldn't", 'where', 'our',
    'other', 'both', "won't", 'into', "here's", 'while', 'yours', "you'd",
    "they're", 'yourself', "they'd", 'had', 'is', 'of', "he'd", "they've",
    "mustn't", "you're", 'which', 'nor', 'or', 'from', 'been', 'how', "hadn't",
    "weren't", 'as', "doesn't", 'during', 'they', 'should', "didn't", 'then',
    'have', 'if', 'here', "we've", 'each', "who's", "it's", 'about', "they'll"
}

class YearFilterReporter:
    def describe(self, exprs):
        gt_year = lt_year = None
        for expr in exprs:
            if isinstance(expr._value, YearGTEValue):
                if not gt_year or expr._value.value > gt_year:
                    gt_year = expr._value.value
            elif isinstance(expr._value, YearEqualsValue):
                if not gt_year or expr._value.value > gt_year:
                    gt_year = expr._value.value
                if not lt_year or expr._value.value < lt_year:
                    lt_year = expr._value.value
            else:
                if not lt_year or expr._value.value < lt_year:
                    lt_year = expr._value.value
        if gt_year and lt_year:
            if gt_year == lt_year:
                return 'from {}'.format(gt_year)
            else:
                return 'between {} and {}'.format(gt_year, lt_year)
        elif gt_year:
            return 'after {}'.format(gt_year)
        else:
            return 'before {}'.format(lt_year)


class DonorFilterReporter:
    def __init__(self, verb):
        self.verb = verb
    def describe(self, exprs):
        words = [str(expr.object.display_format()) for expr in exprs]
        if len(words) == 1:
            clauses = words[0]
        else:
            clauses = ' and '.join([', '.join(words[:-1]), words[-1]])
        return "{verb} {clauses}".format(verb=self.verb, clauses=clauses)

class GenericFilterReporter:
    def __init__(self, verb):
        self.verb = verb
    def describe(self, exprs):
        words = [str(expr.str if hasattr(expr, "str") else expr._value.value) for expr in exprs]
        if len(words) == 1:
            clauses = words[0]
        else:
            clauses = ' and '.join([', '.join(words[:-1]), words[-1]])
        return "{verb} {clauses}".format(verb=self.verb, clauses=clauses)

class LocationFilterReporter:
    def describe(self, exprs):
        location = {}
        for expr in exprs:
            if isinstance(expr._value, CountyValue):
                location['county'] = expr._value.value
            elif isinstance(expr._value, CityValue):
                location['city'] = expr._value.value
            elif isinstance(expr._value, StateValue):
                location['state'] = expr._value.value
            elif isinstance(expr._value, CountryValue):
                location['country'] = expr._value.value
        return 'from ' + models.format_location(**location)

class MaxReporter:
    def describe(self, exprs):
        return ', '.join(self.describe_(expr) for expr in exprs)
    def describe_(self, expr):
        if isinstance(expr, Maximum):
            return self.describe_(expr.left)
        else:
            return expr.str if hasattr(expr, 'str') else str(expr._value.value)

class CollectionReporter:
    def describe(self, exprs):
        return ', '.join(expr.name for expr in exprs)

class NewPhotosReporter:
    def describe(self, exprs):
        return "new" if exprs[0]._value.value else 'not new'

class Description:
    def __init__(self, values):
        self.values = values

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.values == other.values

    def __add__(self, other):
        return self.__class__(self.values + other.values)

    def formatter(self, group):
        if group == 'max':
            return MaxReporter()
        if group == 'year':
            return YearFilterReporter()
        if group == 'location':
            return LocationFilterReporter()
        if group == 'caption':
            return GenericFilterReporter('captioned with')
        if group == 'term':
            return GenericFilterReporter('termed with')
        if group == 'donor_lastname':
            return GenericFilterReporter('donor has last name')
        if group == 'tag':
            return GenericFilterReporter('tagged with')
        if group == 'photographer':
            return DonorFilterReporter('photographed by')
        if group == 'donor':
            return DonorFilterReporter('contributed by')
        if group == 'new':
            return NewPhotosReporter()
        if group == 'user-collection':
            return CollectionReporter()

    def __str__(self):
        by_group = {}
        for v in self.values:
            category = v.group()
            exprs = by_group.get(category, [])
            exprs.append(v)
            by_group[category] = exprs
        groups = reversed(sorted(by_group.keys()))
        group_descriptions = [self.formatter(group).describe(by_group[group]) for group in groups]
        if len(group_descriptions) == 1:
            return group_descriptions[0]
        return '; and '.join(['; '.join(group_descriptions[:-1]), group_descriptions[-1]])

@dataclass
class Expression:
    _value: Any = None

    def __or__(self, obj):
        return Or(self, obj)

    def __and__(self, obj):
        return And(self, obj)

    def __invert__(self):
        return Not(self)

    def __str__(self):
        return self._value.serialize()

    def shakeout(self):
        if self._value.shakeout():
            return None
        return self

    def is_collection(self):
        return self._value.is_collection()

    @property
    def object(self):
        return self._value.object

    def select_related(self, user=None):
        return self._value.matching_photos(queryset=self._value.get_related_queryset())

    def get_search_args(self, user=None):
        return []

    def select_objects(self, user=None):
        return self._value.filter_related(related=self.select_related(user=user))

    def filter(self, user=None):
        return Q(*self.get_search_args(user=user), **self.get_search_kwargs())

    def get_search_kwargs(self):
        return {}

    def get_score(self, user=None):
        return Case(When(self.filter(user), then=1), default=0, output_field=FloatField())

    def scoreF(self, negated, user):
        score = self.get_score(user=user)
        if negated:
            return 1 - score
        return score

    def as_collection(self, qs, user):
        q = self.filter(user)
        r = qs.filter(q).order_by('year', 'id')
        return r

    def as_search(self, qs, user):
        q = self.filter(user)
        r = qs.filter(q).annotate(relevance=self.scoreF(False, user)).order_by('-relevance', 'year', 'id')
        return r

    def description(self):
        return Description([self])

    def short_label(self):
        return self._value.short_label()

    def group(self):
        return self._value.group()

    @property
    def name(self):
        return self._value.name()

class SubqueryExpression(Expression):
    def get_search_args(self, user=None):
        return [Exists(self.select_objects(user=user))]

    def get_score(self, user=None):
        return self._value.get_subquery(query=self.select_objects(user=user))

class SimpleExpression(Expression):
    def get_search_kwargs(self):
        return {self._value.get_search_field(): self._value.get_search_value()}

class MultiWordCaptionExpression(SimpleExpression):
    def get_score(self, user=None):
        return self._value.get_score(user=user)

class IsNewExpression(Expression):
    def get_search_kwargs(self):
        if not models.NewCutoff.objects.exists():
            return {}
        return {self._value.get_search_field(): self._value.get_search_value()}

class ExactMatchExpression(Expression):
    def get_search_args(self, user=None):
        if self.object:
            return [Exists(self.select_objects(user=user))]
        return []

    def get_search_kwargs(self):
        if self.object:
            return {}
        return {self._value.get_search_field(): self._value.get_search_value()}

class ValueBase:
    def shakeout(self):
        return False

    def is_collection(self):
        return True

    def matching_photos(self, *, queryset):
        return queryset.filter(photo__id=OuterRef('pk'))

    @cached_property
    def object(self):
        if not hasattr(self.value, "id"):
            try:
                return self.get_exact_object()
            except (ValidationError, ValueError, ObjectDoesNotExist):
                return None
        return self.value

    def name(self):
        return self.object.name

@dataclass
class SingleWordValueBase(ValueBase):
    value: str

    def get_subquery(self, *, query):
        return Subquery(query.annotate(total=Sum('count')).values('total'))

    def filter_related(self, *, related):
        return related.filter(word=self.value, field=self.wordcount_field())

    def get_related_queryset(self, *, user=None):
        return models.WordCount.objects.all()

class SingleWordTagValue(SingleWordValueBase):
    def serialize(self):
        return 'tag:{}'.format(self.value)

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def wordcount_field(self):
        return 'TA'

    def group(self):
        return "tag"

class SingleWordTermValue(SingleWordValueBase):
    def serialize(self):
        return 'term:{}'.format(self.value)

    def short_label(self):
        return "Term: {}".format(self.value.lower())

    def wordcount_field(self):
        return 'TE'

    def group(self):
        return "term"

class SingleWordCaptionValue(SingleWordValueBase):
    def serialize(self):
        return 'caption:{}'.format(self.value)

    def shakeout(self):
        return self.value in STOPWORDS

    def is_collection(self):
        return False

    def wordcount_field(self):
        return 'CA'

class MultiWordValueBase(ValueBase):
    def get_subquery(self, *, query):
        field = self.get_annotation_match_field()
        return Subquery(
            query.values('photo__id').annotate(
                removed=Sum(Length(Replace(Lower(F(field)), Value(self.value)))),
                total=Sum(Length(F(field))),
                perc=F('removed')*1.0/F('total'),
            ).values('perc'))

@dataclass
class MultiWordTagValue(MultiWordValueBase):
    value: str
    def serialize(self):
        return 'tag:"{}"'.format(self.value)

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def get_annotation_match_field(self):
        return "tag__tag"

    def filter_related(self, *, related=None):
        return related.filter(tag__tag__icontains=self.value)

    def get_related_queryset(self, *, user=None):
        return models.PhotoTag.objects.filter(accepted=True)

    def group(self):
        return "tag"

@dataclass
class MultiWordTermValue(MultiWordValueBase):
    value: str

    def serialize(self):
        return 'term:"{}"'.format(self.value)

    def short_label(self):
        return "Term: {}".format(self.value.lower())

    def get_annotation_match_field(self):
        return "term"

    def filter_related(self, *, related):
        return related.filter(term__icontains=self.value)

    def get_related_queryset(self, *, user=None):
        return models.Term.objects.all()

    def group(self):
        return "term"

@dataclass
class MultiWordCaptionValue(ValueBase):
    value: str

    def serialize(self):
        return 'caption:"{}"'.format(self.value)

    def get_score(self, *, user):
        caption_minusval = Cast(Length(Replace(Lower(F('caption')), Value(self.value))), FloatField())
        captionlen = Cast(Greatest(1.0, Length('caption')), FloatField())
        return caption_minusval / captionlen

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "caption__icontains"

    def is_collection(self):
        return False


@dataclass
class TagExactlyValue(ValueBase):
    value: str

    def serialize(self):
        return 'tag_exact:"{}"'.format(self.value)

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def get_search_value(self):
        return []

    def get_search_field(self):
        return "id__in"

    def filter_related(self, *, related):
        return related.filter(tag__id=self.object.id)

    def get_exact_object(self):
        return models.Tag.objects.get(tag__iexact=self.value)

    def get_related_queryset(self, *, user=None):
        return models.PhotoTag.objects.filter(accepted=True)

    def group(self):
        return "tag"

@dataclass
class TermExactlyValue(ValueBase):
    value: str

    def serialize(self):
        return 'term_exact:{}'.format(self.value)

    def short_label(self):
        return "Term: {}".format(self.value.lower())

    def get_search_value(self):
        return []

    def get_search_field(self):
        return "id__in"

    def filter_related(self, *, related):
        return related.filter(id=self.object.id)

    def get_exact_object(self):
        return models.Term.objects.get(term__iexact=self.value)

    def get_related_queryset(self, *, user=None):
        return models.Term.objects.all()

    def group(self):
        return "term"

@dataclass
class PhotographerExactlyValue(ValueBase):
    value: str

    def serialize(self):
        return 'photographer_exact:{}'.format(self.value.id)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "photographer__id"

    def get_exact_object(self):
        return models.Donor.objects.get(id=self.value)

    def group(self):
        return 'photographer'

@dataclass
class DonorValue(ValueBase):
    value: str

    def serialize(self):
        return 'contributor:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "donor__last_name__iexact"

    def group(self):
        return 'donor_lastname'

@dataclass
class AccessionValue(ValueBase):
    value: int

    def serialize(self):
        return 'FI{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "id"

@dataclass
class StateValue(ValueBase):
    value: str

    def serialize(self):
        return 'state:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "state__icontains"

    def group(self):
        return 'location'

@dataclass
class CountyValue(ValueBase):
    value: str

    def serialize(self):
        return 'county:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "county__iexact"

    def group(self):
        return 'location'

@dataclass
class CountryValue(ValueBase):
    value: str

    def serialize(self):
        return 'country:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "country__iexact"

    def group(self):
        return 'location'

@dataclass
class CityValue(ValueBase):
    value: str

    def serialize(self):
        return 'city:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "city__iexact"

    def group(self):
        return 'location'

@dataclass
class YearEqualsValue(ValueBase):
    value: int

    def serialize(self):
        return 'year:{}'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "year"

    def group(self):
        return 'year'

@dataclass
class YearGTEValue(ValueBase):
    value: int

    def serialize(self):
        return 'year:{}+'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "year__gte"

    def group(self):
        return 'year'
@dataclass
class YearLTEValue(ValueBase):
    value: int

    def serialize(self):
        return 'year:{}-'.format(self.value)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "year__lte"

    def group(self):
        return 'year'

@dataclass
class DonorExactlyValue(ValueBase):
    value: str

    def serialize(self):
        return 'contributor_exact:{}'.format(self.value.id)

    def get_search_value(self):
        return self.value

    def get_search_field(self):
        return "donor"

    def get_exact_object(self):
        return models.Donor.objects.get(pk=int(self.value))

    def group(self):
        return 'donor'

@dataclass
class UserCollectionValue(ValueBase):
    value: str
    def serialize(self):
        return 'collection:{}'.format(self.value)

    def name(self):
        if not self.object:
            return ""
        return self.object.name

    def short_label(self):
        return 'Collection: {}'.format(self.name())

    def get_search_value(self):
        return []

    def get_search_field(self):
        return "id__in"

    def filter_related(self, *, related):
        return related.filter(uuid=self.value)

    def get_exact_object(self):
        return models.Collection.objects.get(uuid=self.value)

    def get_related_queryset(self, *, user=None):
        visibility_filter = ~Q(visibility='PR')
        if user.is_authenticated:
            visibility_filter |= Q(owner=user)
        return models.Collection.objects.filter(visibility_filter)

    def group(self):
        return "user-collection"

    def matching_photos(self, *, queryset):
        return queryset.filter(photos=OuterRef('pk'))

@dataclass
class IsNewValue(ValueBase):
    value: bool

    def serialize(self):
        return 'is_new:{}'.format(self.value).lower()

    def short_label(self):
            return "New: {}".format(self.value)

    def get_search_value(self):
        return models.NewCutoff.objects.all()[0].date

    def get_search_field(self):
        if self.value:
            return "created__gte"
        else:
            return "created__lte"

    def group(self):
        return "new"


def UserCollection(value):
    return ExactMatchExpression(_value=UserCollectionValue(value))

def IsNew(value):
    return IsNewExpression(_value=IsNewValue(value))

def TermExactly(value):
    return ExactMatchExpression(_value=TermExactlyValue(value))

def PhotographerExactly(value):
    return SimpleExpression(_value=PhotographerExactlyValue(value))

def DonorExactly(value):
    return SimpleExpression(_value=DonorExactlyValue(value))

def Donor(value):
    return SimpleExpression(_value=DonorValue(value.lower()))

def AccessionNumber(value):
    return SimpleExpression(_value=AccessionValue(value))

def MultiWordTag(value):
    return SubqueryExpression(_value=MultiWordTagValue(value.lower()))

def TagExactly(value):
    return ExactMatchExpression(_value=TagExactlyValue(value))

def SingleWordTag(value):
    return SubqueryExpression(_value=SingleWordTagValue(value))

Tag = lambda s: MultiWordTag(s) if len(s.split()) > 1 else SingleWordTag(s)
CollectionTag = lambda s: MultiWordTag(s) if len(s.split()) > 1 else SingleWordTag(s)

def MultiWordTerm(value):
    return SubqueryExpression(_value=MultiWordTermValue(value.lower()))

def SingleWordTerm(value):
    return SubqueryExpression(_value=SingleWordTermValue(value.lower()))

Term = lambda s: MultiWordTerm(s) if len(s.split()) > 1 else SingleWordTerm(s)

def MultiWordCaption(value):
    return MultiWordCaptionExpression(_value=MultiWordCaptionValue(value.lower()))

def SingleWordCaption(value):
    return SubqueryExpression(_value=SingleWordCaptionValue(value.lower()))

Caption = lambda s: MultiWordCaption(s) if len(s.split()) > 1 else SingleWordCaption(s)

def State(value):
    return SimpleExpression(_value=StateValue(value))

def Country(value):
    return SimpleExpression(_value=CountryValue(value))

def County(value):
    return SimpleExpression(_value=CountyValue(value))

def City(value):
    return SimpleExpression(_value=CityValue(value))

def YearLTE(value):
    return SimpleExpression(_value=YearLTEValue(value))

def YearGTE(value):
    return SimpleExpression(_value=YearGTEValue(value))

def YearEquals(value):
    return SimpleExpression(_value=YearEqualsValue(value))

class Not(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '-({})'.format(self.value)

    def is_collection(self):
        return self.value.is_collection()

    def description(self):
        return self.value.description()

    def short_label(self):
        raise NotImplementedError
    def filter(self, user):
        v = self.value.filter(user)
        return ~v if v else v


    def filter2(self, user):
        v = self.value.filter2(user)
        return ~v if v else v

    def annotations1(self, prefix=''):
        return self.value.annotations1(prefix=prefix+"NOT_")

    def scoreF(self, negated, user):
        return self.value.scoreF(not negated, user)

    def score(self, photo, negated):
        return self.value.score(photo, not negated)

    def shakeout(self):
        value = self.value.shakeout()
        if value:
            return Not(value)
        return value


class BinaryOperator(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, repr(self.left), repr(self.right))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.left == other.left and self.right == other.right

    def filter2(self, user):
        l = self.left.filter2(user)
        r = self.right.filter2(user)
        if l and r:
            return l | r
        return l if l else r

    def annotations1(self, prefix=''):
        return dict(**self.left.annotations1(prefix=prefix+"L_"), **self.right.annotations1(prefix+"R_"))

    def shakeout(self):
        left = self.left.shakeout()
        right = self.right.shakeout()
        if right and left:
            return self.__class__(left, right)
        if right:
            return right
        return left


class Maximum(BinaryOperator):
    def filter(self, user):
        l = self.left.filter(user)
        r = self.right.filter(user)
        if l and r:
            return l | r
        return l or r

    def __str__(self):
        return '({}) | ({})'.format(self.left, self.right)

    def scoreF(self, negated, user):
        if negated:
            return Least(self.left.scoreF(negated, user), self.right.scoreF(negated, user))
        return Greatest(self.left.scoreF(negated, user), self.right.scoreF(negated, user))

    def score(self, photo, negated):
        if negated:
            return min(self.left.score(photo, negated), self.right.score(photo, negated))
        return max(self.left.score(photo, negated) * self.right.score(photo, negated))

    def is_collection(self):
        return self.left.is_collection() and self.right.is_collection()

    def short_label(self):
        return self.left.value

    def group(self):
        return "max"


class And(BinaryOperator):
    def filter(self, user):
        l = self.left.filter(user)
        r = self.right.filter(user)
        if l and r:
            return l & r
        return l or r

    def __str__(self):
        return '({}) AND ({})'.format(self.left, self.right)

    def scoreF(self, negated, user):
        if negated:
            return self.left.scoreF(negated, user) + self.right.scoreF(negated, user)
        return self.left.scoreF(negated, user) * self.right.scoreF(negated, user)

    def score(self, photo, negated):
        if negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)

    def is_collection(self):
        return self.left.is_collection() and self.right.is_collection()

    def description(self):
        return self.left.description() + self.right.description()

    def short_label(self):
        raise NotImplementedError

class Or(BinaryOperator):
    def filter(self, user):
        l = self.left.filter(user)
        r = self.right.filter(user)
        if l and r:
            return l | r
        return l or r

    def __str__(self):
        return '{} OR {}'.format(self.left, self.right)

    def scoreF(self, negated, user):
        if negated:
            return self.left.scoreF(negated, user) * self.right.scoreF(negated, user)
        return self.left.scoreF(negated, user) + self.right.scoreF(negated, user)

    def is_collection(self):
        return False

    def score(self, photo, negated):
        if not negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)

    def description(self):
        raise NotImplemented

    def short_label(self):
        raise NotImplementedError

def Any(s):
    expr = Or(Donor(s), Or(Caption(s), Or(State(s), Or(Country(s), Or(County(s), Or(City(s), Or(Tag(s), Term(s))))))))
    try:
        expr = Or(YearEquals(int(s)), expr)
    except:
        pass
    return expr

def CollectionExpr(s):
    expr = Maximum(CollectionTag(s), Maximum(Term(s), Maximum(City(s), Maximum(State(s), Maximum(Country(s), County(s))))))
    try:
        expr = Maximum(YearEquals(int(s)), expr)
    except:
        pass
    return expr
