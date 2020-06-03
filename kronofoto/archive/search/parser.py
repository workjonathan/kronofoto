import parsy
from .expression import *

number = parsy.regex(r'-?[0-9]+').map(int)
quoted = parsy.string('"') >> parsy.regex(r'[^"]*') << parsy.string('"')
string = quoted | parsy.regex(r'[^\s\(\)]+')

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


negate = lambda expr: ((parsy.string('-') >> parsy.whitespace.optional() >> expr.map(Not)) | expr)
wrap = lambda expr: parsy.string('(').mark() >> parsy.whitespace.optional() >> expr << parsy.whitespace.optional() << parsy.string(')')

@parsy.generate
def expr():
    e = yield andExpr
    es = yield (
        (parsy.whitespace.optional() >> (parsy.string('OR') >> parsy.whitespace.optional()).optional()) >> andExpr
    ).many()
    for e2 in es:
        e = Or(e, e2)
    return parsy.success(e)


@parsy.generate
def andExpr():
    e = yield simpleExpr
    es = yield (
        parsy.whitespace.optional() >> parsy.string('AND') >> parsy.whitespace.optional() >> simpleExpr
    ).many()
    for e2 in es:
        e = And(e, e2)
    return parsy.success(e)


simpleExpr = negate(
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
    string.map(Any) |
    wrap(expr)
)


def parse(s):
    parser = parsy.whitespace.optional() >> expr << parsy.whitespace.optional() << parsy.eof
    try:
        return parser.parse(s)
    except parsy.ParseError as err:
        if ')' in err.expected:
            raise ExpectedParenthesis from err
        elif s[err.index] == ')':
            raise UnexpectedParenthesis(err.index) from err


class UnexpectedParenthesis(BaseException):
    def __init__(self, index):
        self.index = index


class ExpectedParenthesis(BaseException):
    pass
