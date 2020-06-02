import parsy
from .expression import *

number = parsy.regex(r'-?[0-9]+').map(int)
quoted = parsy.string('"') >> parsy.regex(r'[^"]*') << parsy.string('"')
string = quoted | parsy.regex(r'[^\s]+')

yearExpr = parsy.string('year:') >> number.map(YearEquals)
tagExpr = parsy.string('tag:') >> string.map(Tag)
donorExpr = parsy.string('donor:') >> string.map(Donor)
termExpr = parsy.string('term:') >> string.map(Term)
cityExpr = parsy.string('city:') >> string.map(City)
stateExpr = parsy.string('state:') >> string.map(State)
countryExpr = parsy.string('country:') >> string.map(Country)
countyExpr = parsy.string('county:') >> string.map(County)
captionExpr = parsy.string('caption:') >> string.map(Caption)
accessionExpr = parsy.string('FI') >> number.map(AccessionNumber)


negate = lambda expr: expr | (parsy.string('-') >> expr.map(Not))

@parsy.generate
def simpleExpr():
    e = yield negate(
        yearExpr |
        tagExpr |
        donorExpr |
        termExpr |
        cityExpr |
        stateExpr |
        countryExpr |
        countyExpr |
        accessionExpr |
        captionExpr |
        parsy.string("(") >> expr << parsy.string(")")
    ) | parsy.string('-') >> string.map(Any).map(Not) | string.map(Any)
    return parsy.success(e)


@parsy.generate
def andExpr():
    e = yield simpleExpr
    es = yield (
        parsy.whitespace >> parsy.string('AND') >> parsy.whitespace >> simpleExpr
    ).many()
    exprs = list(reversed(es))
    exprs.append(e)
    e = exprs[0]
    for e2 in exprs[1:]:
        e = And(e2, e)
    return parsy.success(e)


@parsy.generate
def expr():
    e = yield andExpr
    es = yield (
        (parsy.whitespace >> (parsy.string('OR') >> parsy.whitespace).optional()) >> andExpr
    ).many()
    exprs = list(reversed(es))
    exprs.append(e)
    e = exprs[0]
    for e2 in exprs[1:]:
        e = Or(e2, e)
    return parsy.success(e)


def parse(s):
    parser = expr << parsy.eof
    return parser.parse(s)
