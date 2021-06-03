from django.db.models import Q, F, Value, Case, When, IntegerField, Sum, FloatField, BooleanField
from django.db.models.functions import Cast, Length, Lower, Replace, Greatest, Least, StrIndex
from .. import models

from functools import reduce
import operator
import re

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
            if isinstance(expr, YearGTE):
                if not gt_year or expr.value > gt_year:
                    gt_year = expr.value
            elif isinstance(expr, YearEquals):
                if not gt_year or expr.value > gt_year:
                    gt_year = expr.value
                if not lt_year or expr.value < lt_year:
                    lt_year = expr.value
            else:
                if not lt_year or expr.value < lt_year:
                    lt_year = expr.value
        if gt_year and lt_year:
            if gt_year == lt_year:
                return 'from {}'.format(gt_year)
            else:
                return 'between {} and {}'.format(gt_year, lt_year)
        elif gt_year:
            return 'after {}'.format(gt_year)
        else:
            return 'before {}'.format(lt_year)


class GenericFilterReporter:
    def __init__(self, verb):
        self.verb = verb
    def describe(self, exprs):
        words = [str(expr.value) for expr in exprs]
        if len(words) == 1:
            clauses = words[0]
        else:
            clauses = ' and '.join([', '.join(words[:-1]), words[-1]])
        return "{verb} {clauses}".format(verb=self.verb, clauses=clauses)

class LocationFilterReporter:
    def describe(self, exprs):
        location = {}
        for expr in exprs:
            if isinstance(expr, County):
                location['county'] = expr.value
            elif isinstance(expr, City):
                location['city'] = expr.value
            elif isinstance(expr, State):
                location['state'] = expr.value
            elif isinstance(expr, Country):
                location['country'] = expr.value
        return 'from ' + models.format_location(**location)

class MaxReporter:
    def describe(self, exprs):
        return ', '.join(self.describe_(expr) for expr in exprs)
    def describe_(self, expr):
        if isinstance(expr, Maximum):
            return self.describe_(expr.left)
        else:
            return expr.value

class CollectionReporter:
    def describe(self, exprs):
        return ', '.join(expr.name for expr in exprs)

class NewPhotosReporter:
    def describe(self, exprs):
        return "new" if exprs[0].value else 'not new'

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
        if group == 'term':
            return GenericFilterReporter('termed with')
        if group == 'tag':
            return GenericFilterReporter('tagged with')
        if group == 'donor':
            return GenericFilterReporter('donated by')
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


class Expression:
    def __or__(self, obj):
        return Or(self, obj)

    def __and__(self, obj):
        return And(self, obj)

    def __invert__(self):
        return Not(self)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.value))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.value == other.value

    def __str__(self):
        raise NotImplementedError

    def shakeout(self):
        return self

    def filter1(self, user):
        return None

    def filter2(self, user):
        return None

    def annotations1(self):
        "This should copy data from wordcount_count to something like ca_dog. So {'ca_dog': When(etc)}"
        return {}

    def is_collection(self):
        return False

    def _filter(self, qs, user):
        f2 = self.filter2(user)
        f1 = self.filter1(user)
        q = (f1 | f2) if f1 and f2 else f1 if f1 else f2

        return (qs.filter(q)
            .annotate(**{k: Sum(v, output_field=FloatField()) for (k, v) in self.annotations1().items()})
            .defer(*(f.name for f in models.Photo._meta.fields))
            .annotate(relevance=self.scoreF(False))
            .filter(relevance__gt=0)
        )

    def as_collection(self, qs, user):
        return self._filter(qs, user).order_by('year', 'id')

    def as_search(self, qs, user):
        return self._filter(qs, user).order_by('-relevance', 'year', 'id')

    def description(self):
        return Description([self])

    def short_label(self):
        raise NotImplementedError

    def group(self):
        raise NotImplementedError



class UserCollection(Expression):
    def __init__(self, value):
        self.value = value
        self._object = None

    def __str__(self):
        return 'collection:{}'.format(self.value)

    def filter2(self, user):
        uuid_filter = Q(collection__uuid=self.value)
        visibility_filter = ~Q(collection__visibility='PR')
        if user.is_authenticated:
            visibility_filter |= Q(collection__owner=user)
        return uuid_filter & visibility_filter

    def scoreF(self, negated):
        if not negated:
            return Case(When(collection__uuid=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(collection__uuid=self.value, then=0), default=1, output_field=FloatField())

    @property
    def object(self):
        if not self._object:
            self._object = models.Collection.objects.get(uuid=self.value)
        return self._object

    @property
    def name(self):
        return self.object.name

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return 'Collection: {}'.format(self.name)

    def group(self):
        return 'user-collection'


class IsNew(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'is_new:{}'.format(self.value).lower()

    def filter1(self, user):
        if models.NewCutoff.objects.exists():
            cutoff = models.NewCutoff.objects.all()[0].date
            if self.value:
                return Q(created__gte=cutoff)
            else:
                return Q(created__lt=cutoff)
        return Q()

    def scoreF(self, negated):
        if models.NewCutoff.objects.exists():
            cutoff = models.NewCutoff.objects.all()[0].date
            if (not negated) ^ (not self.value):
                return Case(When(created__gte=cutoff, then=1), default=0, output_field=FloatField())
            else:
                return Case(When(created__lt=cutoff, then=1), default=0, output_field=FloatField())
        else:
            return 1

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "New: {}".format(self.value.term.lower())

    def group(self):
        return "new"


class TermExactly(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'term_exact:{}'.format(self.value)

    def filter1(self, user):
        return Q(terms__id=self.value.id)

    def scoreF(self, negated):
        if not negated:
            return Case(When(terms__id=self.value.id, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(terms__id=self.value.id, then=0), default=1, output_field=FloatField())

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "Term: {}".format(self.value.term.lower())

    def group(self):
        return "term"


class DonorExactly(Expression):
    def __init__(self, value):
        try:
            value = models.Donor.objects.get(pk=int(value))
        except ValueError:
            pass
        except TypeError:
            pass
        self.value = value

    def __str__(self):
        return 'donor_exact:{}'.format(self.value.id)

    def filter1(self, user):
        return Q(donor__id=self.value.id)

    def scoreF(self, negated):
        if not negated:
            return Case(When(donor__id=self.value.id, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(donor__id=self.value.id, then=0), default=1, output_field=FloatField())

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "Donor: {}".format(self.value)

    def group(self):
        return "donor"


class Donor(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def __str__(self):
        return 'donor:{}'.format(self.value)

    def filter1(self, user):
        q = Q(donor__last_name__icontains=self.value) | Q(donor__first_name__icontains=self.value)
        return q

    def scoreF(self, negated):
        lastname_minusval = Cast(Length(Replace(Lower(F('donor__last_name')), Value(self.value))), FloatField())
        lastnamelen = Cast(Greatest(1.0, Length('donor__last_name')), FloatField())
        lastnamebadness = lastname_minusval / lastnamelen
        firstname_minusval = Cast(Length(Replace(Lower(F('donor__first_name')), Value(self.value))), FloatField())
        firstnamelen = Cast(Greatest(1, Length('donor__first_name', output_field=FloatField())), FloatField())
        firstnamebadness = firstname_minusval / firstnamelen

        if negated:
            score = firstnamebadness * lastnamebadness
        else:
            score = 2 - firstnamebadness - lastnamebadness
        return score ** 4 # raising to fourth power pushes the score down unless the name is very close to an exact match.

    def score(self, photo, negated):
        ln = fn = 0
        if not negated:
            if self.value in photo.donor.last_name.lower():
                ln = 1
            if self.value in photo.donor.first_name.lower():
                fn = 1
            return ln + fn
        else:
            if photo.donor.last_name != self.value:
                ln = 1
            if photo.donor.first_name != self.value:
                fn = 1
            return ln * fn


class AccessionNumber(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'FI{}'.format(self.value)

    def filter1(self, user):
        q = Q(id=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(id=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(id=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        if negated and photo.id != self.value:
            return 1
        elif photo.id == self.value:
            return 1
        else:
            return 0


class MultiWordTag(Expression):
    def __init__(self, value):
        self.value = value.lower()
        self.field = 'TA_' + '_'.join(self.value.split())

    def __str__(self):
        return 'tag:"{}"'.format(self.value)

    def filter2(self, user):
        return Q(phototag__tag__tag__icontains=self.value) & Q(phototag__accepted=True)


    def annotations1(self):
        tag_minusval = Cast(
            Length(Replace(Lower(F('phototag__tag__tag')), Value(self.value))), FloatField()
        )
        taglen = Cast(Greatest(1.0, Length('phototag__tag__tag')), FloatField())
        return {self.field: Case(When(phototag__tag__tag__isnull=False, then=1-tag_minusval/taglen), default=0, output_field=FloatField())}


    def scoreF(self, negated):
        if not negated:
            return F(self.field)
        return 1 - F(self.field)

class BasicTag(MultiWordTag):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field = 'B' + self.field

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def group(self):
        return "tag"

class TagExactly(Expression):
    def __init__(self, value):
        self.value = value
        self.field = 'TAE_' + '_'.join(self.value.split())

    def __str__(self):
        return 'tag_exact:"{}"'.format(self.value)

    def filter2(self, user):
        return Q(phototag__tag__tag__iexact=self.value)

    def annotations1(self):
        return {
            self.field: Case(
                When(phototag__tag__tag__iexact=self.value, then=1),
                default=0,
                output_field=FloatField(),
            )
        }

    def scoreF(self, negated):
        if negated:
            return 1 - F(self.field)
        else:
            return F(self.field)

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def group(self):
        return "tag"


class SingleWordTag(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def __str__(self):
        return 'tag:{}'.format(self.value)

    def filter2(self, user):
        return Q(wordcount__word__icontains=self.value, wordcount__field='TA')

    def annotations1(self):
        return {'TA_' + self.value: Case(When(wordcount__word=self.value, then=F('wordcount__count')), default=0.0, output_field=FloatField())}

    def scoreF(self, negated):
        if negated:
            return 1 - F('TA_' + self.value)
        else:
            return F('TA_' + self.value)

    def score(self, photo, negated):
        scores = []
        for tag in photo.tags.filter(phototag__accepted=True):
            words = [w.lower() for w in tag.tag.split()]
            scores.append(sum(1 for w in words if not negated and self.value == w or negated and self.value != w)/len(words))
        if not negated:
            return sum(scores)
        return reduce(operator.mul, scores, 1)

    def is_collection(self):
        return True

    def description(self):
        return Description([self])

    def short_label(self):
        return "Tag: {}".format(self.value.lower())

    def group(self):
        return "tag"

Tag = lambda s: MultiWordTag(s) if len(s.split()) > 1 else SingleWordTag(s)


class MultiWordTerm(Expression):
    def __init__(self, value):
        self.value = value.lower()
        self.field = 'TE_' + '_'.join(self.value.split())

    def __str__(self):
        return 'term:"{}"'.format(self.value)

    def filter1(self, user):
        return Q(terms__term__icontains=self.value)

    def annotations1(self):
        term_minusval = Cast(
            Length(Replace(Lower(F('terms__term')), Value(self.value))), FloatField()
        )
        termlen = Cast(Greatest(1.0, Length('terms__term')), FloatField())
        return {self.field: Case(When(terms__term__isnull=False, then=1 - term_minusval/termlen), default=0.0, output_field=FloatField())}


    def scoreF(self, negated):
        if not negated:
            return F(self.field)
        return 1 - F(self.field)

    def short_label(self):
        return "Term: {}".format(self.value)

    def group(self):
        return "term"

    def is_collection(self):
        return True

    def description(self):
        return Description([self])


class SingleWordTerm(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def __str__(self):
        return 'term:{}'.format(self.value)

    def filter2(self, user):
        return Q(wordcount__word__icontains=self.value, wordcount__field='TE')

    def annotations1(self):
        return {'TE_' + self.value: Case(When(wordcount__word__icontains=self.value, then=F('wordcount__count')), default=0.0, output_field=FloatField())}

    def scoreF(self, negated):
        if negated:
            return 1 - F('TE_' + self.value)
        else:
            return F('TE_' + self.value)

    def score(self, photo, negated):
        scores = []
        for term in photo.terms.filter(term__icontains=self.value):
            words = [w.lower() for w in term.term.split()]
            scores.append(sum(1 for w in words if not negated and self.value == w or negated and self.value != w)/len(words))
        if not negated:
            return sum(scores)
        return reduce(operator.mul, scores, 1)

    def is_collection(self):
        return True

    def short_label(self):
        return "Term: {}".format(self.value)

    def group(self):
        return "term"

    def description(self):
        return Description([self])

Term = lambda s: MultiWordTerm(s) if len(s.split()) > 1 else SingleWordTerm(s)

class MultiWordCaption(Expression):
    def __init__(self, value):
        self.value = value.lower()
        self.caption_minusval = Cast(Length(Replace(Lower(F('caption')), Value(self.value))), FloatField())
        self.captionlen = Cast(Greatest(1.0, Length('caption')), FloatField())

    def __str__(self):
        return 'caption:"{}"'.format(self.value)

    def filter1(self, user):
        return Q(caption__icontains=self.value)

    def scoreF(self, negated):
        score = self.caption_minusval / self.captionlen

        if not negated:
            score = 1 - score
        return score

class SingleWordCaption(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def __str__(self):
        return 'caption:{}'.format(self.value)

    def shakeout(self):
        if self.value in STOPWORDS:
            return None
        return self

    def filter2(self, user):
        return Q(wordcount__word=self.value, wordcount__field='CA')

    def annotations1(self):
        return {'CA_' + self.value: Case(When(wordcount__word=self.value, then=F('wordcount__count')), default=0.0, output_field=FloatField())}

    def scoreF(self, negated):
        if negated:
            return 1 - F('CA_' + self.value)
        else:
            return F('CA_' + self.value)


    def score(self, photo, negated):
        words = [w.lower() for w in re.split(r'\W+', photo.caption)]
        if len(words) == 0:
            return 0 if not negated else 1
        return sum(1 for word in words if (not negated and word == self.value) or (negated and word != self.value))/len(words)

Caption = lambda s: MultiWordCaption(s) if len(s.split()) > 1 else SingleWordCaption(s)

class State(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'state:{}'.format(self.value)

    def filter1(self, user):
        q = Q(state__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(state__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(state__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.state == self.value or negated and photo.state != self.value else 0

    def is_collection(self):
        return True

    def short_label(self):
        return "State: {}".format(self.value)

    def group(self):
        return "location"

class Country(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'country:{}'.format(self.value)

    def filter1(self, user):
        q = Q(country__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(country__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(country__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.country == self.value or negated and photo.country != self.value else 0

    def is_collection(self):
        return True

    def short_label(self):
        return "Country: {}".format(self.value)

    def group(self):
        return "location"

class County(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'county:{}'.format(self.value)

    def filter1(self, user):
        q = Q(county__iexact=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(county__iexact=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(county__iexact=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.county == self.value or negated and photo.county != self.value else 0

    def is_collection(self):
        return True

    def short_label(self):
        return "County: {}".format(self.value)

    def group(self):
        return "location"

class City(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'city:{}'.format(self.value)

    def filter1(self, user):
        q = Q(city__iexact=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(city__iexact=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(city__iexact=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.city == self.value or negated and photo.city != self.value else 0

    def is_collection(self):
        return True

    def short_label(self):
        return "City: {}".format(self.value)

    def group(self):
        return "location"


class YearLTE(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'year:{}-'.format(self.value)

    def filter1(self, user):
        q = Q(year__lte=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year__lte=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year__lte=self.value, then=0.0), default=1.0, output_field=FloatField())

    def is_collection(self):
        return True

    def short_label(self):
        return "Year: {}-".format(self.value)

    def group(self):
        return "year"


class YearGTE(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'year:{}+'.format(self.value)

    def filter1(self, user):
        q = Q(year__gte=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year__gte=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year__gte=self.value, then=0.0), default=1.0, output_field=FloatField())

    def is_collection(self):
        return True

    def short_label(self):
        return "Year: {}+".format(self.value)

    def group(self):
        return "year"


class YearEquals(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'year:{}'.format(self.value)

    def filter1(self, user):
        q = Q(year=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year=self.value, then=0.0), default=1.0, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.year == self.value or negated and photo.year != self.value else 0

    def is_collection(self):
        return True

    def short_label(self):
        return "Year: {}".format(self.value)

    def group(self):
        return "year"



class Not(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '-({})'.format(self.value)

    def filter1(self, user):
        v = self.value.filter1(user)
        return ~v if v else v

    def filter2(self, user):
        v = self.value.filter2(user)
        return ~v if v else v

    def annotations1(self):
        return self.value.annotations1()

    def scoreF(self, negated):
        return self.value.scoreF(not negated)

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

    def annotations1(self):
        return dict(**self.left.annotations1(), **self.right.annotations1())

    def shakeout(self):
        left = self.left.shakeout()
        right = self.right.shakeout()
        if right and left:
            return self.__class__(left, right)
        if right:
            return right
        return left


class Maximum(BinaryOperator):
    def filter1(self, user):
        l = self.left.filter1(user)
        r = self.right.filter1(user)
        if l and r:
            return l | r
        return l if l else r

    def __str__(self):
        return '({}) | ({})'.format(self.left, self.right)

    def scoreF(self, negated):
        if negated:
            return Least(self.left.scoreF(negated), self.right.scoreF(negated))
        return Greatest(self.left.scoreF(negated), self.right.scoreF(negated))

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
    def filter1(self, user):
        l = self.left.filter1(user)
        r = self.right.filter1(user)
        if l and r:
            return l & r
        return l if l else r

    def __str__(self):
        return '({}) AND ({})'.format(self.left, self.right)

    def scoreF(self, negated):
        if negated:
            return self.left.scoreF(negated) + self.right.scoreF(negated)
        return self.left.scoreF(negated) * self.right.scoreF(negated)

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
    def filter1(self, user):
        l = self.left.filter1(user)
        r = self.right.filter1(user)
        if l and r:
            return l | r
        return l if l else r

    def __str__(self):
        return '{} OR {}'.format(self.left, self.right)

    def scoreF(self, negated):
        if negated:
            return self.left.scoreF(negated) * self.right.scoreF(negated)
        return self.left.scoreF(negated) + self.right.scoreF(negated)

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
    expr = Maximum(Tag(s), Maximum(Term(s), Maximum(City(s), Maximum(State(s), Maximum(Country(s), County(s))))))
    try:
        expr = Maximum(YearEquals(int(s)), expr)
    except:
        pass
    return expr
