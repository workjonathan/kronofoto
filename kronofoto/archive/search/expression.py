from django.db.models import Q
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



class Donor(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(donor__last_name=self.value) | Q(donor__first_name=self.value)
        return q

    def score(self, photo, negated):
        ln = fn = 0
        if not negated:
            if photo.donor.last_name == self.value:
                ln = 1
            if photo.donor.first_name == self.value:
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

    def evaluate(self):
        q = Q(id=self.value)
        return q

    def score(self, photo, negated):
        if negated and photo.id != self.value:
            return 1
        elif photo.id == self.value:
            return 1
        else:
            return 0



class Tag(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(phototag__tag__tag__icontains=self.value) & Q(phototag__accepted=True)
        return q

    def score(self, photo, negated):
        scores = []
        for tag in photo.tags.filter(phototag__accepted=True):
            words = [w.lower() for w in tag.tag.split()]
            scores.append(sum(1 for w in words if not negated and self.value == w or negated and self.value != w)/len(words))
        if not negated:
            return sum(scores)
        return reduce(operator.mul, scores, 1)


class Term(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(terms__term__icontains=self.value)
        return q

    def score(self, photo, negated):
        scores = []
        for term in photo.terms.filter(term__icontains=self.value):
            words = [w.lower() for w in term.split()]
            scores.append(sum(1 for w in words if not negated and self.value == w or negated and self.value != w)/len(words))
        if not negated:
            return sum(scores)
        return reduce(operator.mul, scores, 1)


class Caption(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def shakeout(self):
        if self.value in STOPWORDS:
            return None
        return self

    def evaluate(self):
        return Q(caption__icontains=self.value)

    def score(self, photo, negated):
        words = [w.lower() for w in re.split(r'\W+', photo.caption)]
        if len(words) == 0:
            return 0 if not negated else 1
        return sum(1 for word in words if (not negated and word == self.value) or (negated and word != self.value))/len(words)


class State(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(state__icontains=self.value)
        return q

    def score(self, photo, negated):
        return 1 if not negated and photo.state == self.value or negated and photo.state != self.value else 0


class Country(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(country__icontains=self.value)
        return q

    def score(self, photo, negated):
        return 1 if not negated and photo.country == self.value or negated and photo.country != self.value else 0

class County(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(county__icontains=self.value)
        return q

    def score(self, photo, negated):
        return 1 if not negated and photo.county == self.value or negated and photo.county != self.value else 0


class City(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self):
        q = Q(city__icontains=self.value)
        return q

    def score(self, photo, negated):
        return 1 if not negated and photo.city == self.value or negated and photo.city != self.value else 0

class YearEquals(Expression):
    def __init__(self, value):
        self.value = value

    def evaluate(self):
        q = Q(year=self.value)
        return q

    def score(self, photo, negated):
        return 1 if not negated and photo.year == self.value or negated and photo.year != self.value else 0


class Not(Expression):
    def __init__(self, value):
        self.value = value

    def evaluate(self):
        return ~self.value.evaluate()

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

    def shakeout(self):
        left = self.left.shakeout()
        right = self.right.shakeout()
        if right and left:
            return self.__class__(left, right)
        if right:
            return right
        return left


class And(BinaryOperator):
    def evaluate(self):
        return self.left.evaluate() & self.right.evaluate()

    def score(self, photo, negated):
        if negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)


class Or(BinaryOperator):
    def evaluate(self):
        return self.left.evaluate() | self.right.evaluate()

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
