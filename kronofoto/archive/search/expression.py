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

    def shakeout(self):
        return self

    def filter1(self):
        return None

    def filter2(self):
        return None

    def annotations1(self):
        "This should copy data from wordcount_count to something like ca_dog. So {'ca_dog': When(etc)}"
        return {}

    def as_collection(self):
        raise ValueError('Cannot represent this expression as collection')

class TermExactly(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        return Q(terms__id=self.value.id)

    def scoreF(self, negated):
        if not negated:
            return Case(When(terms__id=self.value.id, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(terms__id=self.value.id, then=0), default=1, output_field=FloatField())

    def as_collection(self):
        return {'term': models.Term.objects.get(pk=self.value.id).slug}


class DonorExactly(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        return Q(donor__id=self.value.id)

    def scoreF(self, negated):
        if not negated:
            return Case(When(donor__id=self.value.id, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(donor__id=self.value.id, then=0), default=1, output_field=FloatField())

    def as_collection(self):
        return {'donor': self.value.id}



class Donor(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def filter1(self):
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

    def filter1(self):
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


    def filter1(self):
        return Q(phototag__tag__tag__icontains=self.value) & Q(phototag__accepted=True)


    def annotations1(self):
        tag_minusval = Cast(
            Length(Replace(Lower(F('phototag__tag__tag')), Value(self.value))), FloatField()
        )
        taglen = Cast(Greatest(1.0, Length('phototag__tag__tag')), FloatField())
        return {self.field: tag_minusval/taglen}


    def scoreF(self, negated):
        if not negated:
            return 1 - F(self.field)
        return F(self.field)

class TagExactly(Expression):
    def __init__(self, value):
        self.value = value
        self.field = 'TAE_' + '_'.join(self.value.split())

    def filter1(self):
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

    def as_collection(self):
        try:
            return {'tag': models.Tag.objects.get(tag__iexact=self.value).slug}
        except models.Tag.DoesNotExist:
            return {'tag': self.value}

class SingleWordTag(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def filter2(self):
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

Tag = lambda s: MultiWordTag(s) if len(s.split()) > 1 else SingleWordTag(s)


class MultiWordTerm(Expression):
    def __init__(self, value):
        self.value = value.lower()
        self.field = 'TE_' + '_'.join(self.value.split())


    def filter1(self):
        return Q(terms__term__icontains=self.value)


    def annotations1(self):
        term_minusval = Cast(
            Length(Replace(Lower(F('terms__term')), Value(self.value))), FloatField()
        )
        termlen = Cast(Greatest(1.0, Length('terms__term')), FloatField())
        return {self.field: term_minusval/termlen}


    def scoreF(self, negated):
        if not negated:
            return 1 - F(self.field)
        return F(self.field)


class SingleWordTerm(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def filter2(self):
        return Q(wordcount__word=self.value, wordcount__field='TE')

    def annotations1(self):
        return {'TE_' + self.value: Case(When(wordcount__word=self.value, then=F('wordcount__count')), default=0.0, output_field=FloatField())}

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

Term = lambda s: MultiWordTerm(s) if len(s.split()) > 1 else SingleWordTerm(s)

class MultiWordCaption(Expression):
    def __init__(self, value):
        self.value = value.lower()
        self.caption_minusval = Cast(Length(Replace(Lower(F('caption')), Value(self.value))), FloatField())
        self.captionlen = Cast(Greatest(1.0, Length('caption')), FloatField())

    def filter1(self):
        return Q(caption__icontains=self.value)

    def scoreF(self, negated):
        score = self.caption_minusval / self.captionlen

        if not negated:
            score = 1 - score
        return score

class SingleWordCaption(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def shakeout(self):
        if self.value in STOPWORDS:
            return None
        return self

    def filter2(self):
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

    def filter1(self):
        q = Q(state__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(state__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(state__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.state == self.value or negated and photo.state != self.value else 0

    def as_collection(self):
        return {'state': self.value}


class Country(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(country__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(country__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(country__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.country == self.value or negated and photo.country != self.value else 0

    def as_collection(self):
        return {'country': self.value}

class County(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(county__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(county__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(county__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.county == self.value or negated and photo.county != self.value else 0

    def as_collection(self):
        return {'county': self.value}


class City(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(city__icontains=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(city__icontains=self.value, then=1), default=0, output_field=FloatField())
        else:
            return Case(When(city__icontains=self.value, then=0), default=1, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.city == self.value or negated and photo.city != self.value else 0

    def as_collection(self):
        return {'city': self.value}


class YearLTE(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(year__lte=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year__lte=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year__lte=self.value, then=0.0), default=1.0, output_field=FloatField())

    def as_collection(self):
        return {'year_atmost': self.value}

class YearGTE(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(year__gte=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year__gte=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year__gte=self.value, then=0.0), default=1.0, output_field=FloatField())

    def as_collection(self):
        return {'year_atleast': self.value}


class YearEquals(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        q = Q(year=self.value)
        return q

    def scoreF(self, negated):
        if not negated:
            return Case(When(year=self.value, then=1.0), default=0.0, output_field=FloatField())
        else:
            return Case(When(year=self.value, then=0.0), default=1.0, output_field=FloatField())

    def score(self, photo, negated):
        return 1 if not negated and photo.year == self.value or negated and photo.year != self.value else 0

    def as_collection(self):
        return {'year': self.value}


class Not(Expression):
    def __init__(self, value):
        self.value = value

    def filter1(self):
        v = self.value.filter1()
        return ~v if v else v

    def filter2(self):
        v = self.value.filter2()
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

    def filter2(self):
        l = self.left.filter2()
        r = self.right.filter2()
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
    def filter1(self):
        l = self.left.filter1()
        r = self.right.filter1()
        if l and r:
            return l | r
        return l if l else r

    def scoreF(self, negated):
        if negated:
            return Least(self.left.scoreF(negated), self.right.scoreF(negated))
        return Greatest(self.left.scoreF(negated), self.right.scoreF(negated))

    def score(self, photo, negated):
        if negated:
            return min(self.left.score(photo, negated), self.right.score(photo, negated))
        return max(self.left.score(photo, negated) * self.right.score(photo, negated))

    def as_collection(self):
        return {**self.left.as_collection(), **self.right.as_collection()}


class And(BinaryOperator):
    def filter1(self):
        l = self.left.filter1()
        r = self.right.filter1()
        if l and r:
            return l & r
        return l if l else r

    def scoreF(self, negated):
        if negated:
            return self.left.scoreF(negated) + self.right.scoreF(negated)
        return self.left.scoreF(negated) * self.right.scoreF(negated)

    def score(self, photo, negated):
        if negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)

    def as_collection(self):
        return {**self.left.as_collection(), **self.right.as_collection()}


class Or(BinaryOperator):
    def filter1(self):
        l = self.left.filter1()
        r = self.right.filter1()
        if l and r:
            return l | r
        return l if l else r

    def scoreF(self, negated):
        if negated:
            return self.left.scoreF(negated) * self.right.scoreF(negated)
        return self.left.scoreF(negated) + self.right.scoreF(negated)

    def score(self, photo, negated):
        if not negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)


def Any(s):
    expr = Or(Donor(s), Or(Caption(s), Or(State(s), Or(Country(s), Or(County(s), Or(City(s), Or(Tag(s), Term(s))))))))
    try:
        expr = Or(YearEquals(int(s)), expr)
    except:
        pass
    return expr
