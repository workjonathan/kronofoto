from django.db.models import Q
from functools import reduce
import operator
import re


class Expression:
    def __or__(self, obj):
        return Or(self, obj)

    def __and__(self, obj):
        return And(self, obj)

    def __invert__(self):
        return Not(self)


class Donor(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self, negated):
        q = Q(donor__last_name=self.value) | Q(donor__first_name=self.value)
        return ~q if negated else q

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

    def evaluate(self, negated):
        q = Q(id=self.value)
        return ~q if negated else q

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

    def evaluate(self, negated):
        q = Q(phototag__tag__tag__icontains=self.value)
        q = ~q if negated else q
        return q & Q(phototag__accepted=True)

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

    def evaluate(self, negated):
        q = Q(terms__term__icontains=self.value)
        return ~q if negated else q

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

    def evaluate(self, negated):
        q = Q(caption__icontains=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        words = [w.lower() for w in re.split(r'\W+', photo.caption)]
        if len(words) == 0:
            return 0 if not negated else 1
        return sum(1 for word in words if (not negated and word == self.value) or (negated and word != self.value))/len(words)


class State(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self, negated):
        q = Q(state__icontains=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        return 1 if not negated and photo.state == self.value or negated and photo.state != self.value else 0


class Country(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self, negated):
        q = Q(country__icontains=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        return 1 if not negated and photo.country == self.value or negated and photo.country != self.value else 0

class County(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self, negated):
        q = Q(county__icontains=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        return 1 if not negated and photo.county == self.value or negated and photo.county != self.value else 0


class City(Expression):
    def __init__(self, value):
        self.value = value.lower()

    def evaluate(self, negated):
        q = Q(city__icontains=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        return 1 if not negated and photo.city == self.value or negated and photo.city != self.value else 0

class YearEquals(Expression):
    def __init__(self, value):
        self.value = value

    def evaluate(self, negated):
        q = Q(year=self.value)
        return ~q if negated else q

    def score(self, photo, negated):
        return 1 if not negated and photo.year == self.value or negated and photo.year != self.value else 0


class Not(Expression):
    def __init__(self, value):
        self.value = value

    def evaluate(self, negated):
        return self.value.evaluate(not negated)

    def score(self, photo, negated):
        return self.value.score(photo, not negated)


class BinaryOperator(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class And(BinaryOperator):
    def evaluate(self, negated):
        if negated:
            return self.left.evaluate(negated) | self.right.evaluate(negated)
        else:
            return self.left.evaluate(negated) & self.right.evaluate(negated)

    def score(self, photo, negated):
        if negated:
            return self.left.score(photo, negated) + self.right.score(photo, negated)
        return self.left.score(photo, negated) * self.right.score(photo, negated)


class Or(BinaryOperator):
    def evaluate(self, negated):
        if negated:
            return self.left.evaluate(negated) & self.right.evaluate(negated)
        else:
            return self.left.evaluate(negated) | self.right.evaluate(negated)

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
