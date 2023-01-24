import parsy
from .expression import *
from functools import reduce
from dataclasses import dataclass

upper = lambda s: s.upper()
singleton = lambda x: [x]
const = lambda x: lambda _: x
is_instance = lambda t: lambda x: isinstance(x, t)
number = parsy.regex(r'-?[0-9]+').map(int)

#numberplus = parsy.regex(r'-?[0-9]+\+').map(int)
quoted = parsy.string('"') >> parsy.regex(r'[^"]*') << parsy.string('"')
string = quoted | parsy.regex(r'[^\s\(\)]+')
boolean = parsy.string('TRUE', transform=upper).map(const(True)) | parsy.string('FALSE', transform=upper).map(const(False))

yearExpr = parsy.string('year:') >> (
      parsy.seq((number << parsy.string('-')).map(YearGTE), number.map(YearLTE)).combine(And)
    | (number << parsy.string('-')).map(YearLTE)
    | (number << parsy.string('+')).map(YearGTE)
    | number.map(YearEquals)
)

tagExpr = parsy.string('tag:') >> string.map(Tag)
tagExactExpr = parsy.string('tag_exact:') >> string.map(TagExactly)
termExactExpr = parsy.string('term_exact:') >> string.map(TermExactly)
donorExpr = parsy.string('contributor:') >> string.map(Donor)
donorExactExpr = parsy.string('contributor_exact:') >> string.map(DonorExactly)
termExpr = parsy.string('term:') >> string.map(Term)
cityExpr = parsy.string('city:') >> string.map(City)
stateExpr = parsy.string('state:') >> string.map(State)
countryExpr = parsy.string('country:') >> string.map(Country)
countyExpr = parsy.string('county:') >> string.map(County)
captionExpr = parsy.string('caption:') >> string.map(Caption)
accessionExpr = parsy.string('FI') >> number.map(AccessionNumber)
isNewExpr = parsy.string('is_new:') >> boolean.map(IsNew)
collectionExpr = parsy.string('collection:') >> string.map(UserCollection)

token = (
      parsy.string('|', transform=upper).map(upper)
    | parsy.string('AND', transform=upper).map(upper)
    | parsy.string('OR', transform=upper).map(upper)
    | isNewExpr
    | collectionExpr
    | yearExpr
    | tagExpr
    | tagExactExpr
    | donorExpr
    | donorExactExpr
    | termExpr
    | termExactExpr
    | cityExpr
    | stateExpr
    | countryExpr
    | countyExpr
    | accessionExpr
    | captionExpr
    | string.map(Any)
)

separator = (
      parsy.whitespace.map(const([]))
    | parsy.regex(r'\s*[-\(\)]\s*').map(lambda s: [s.strip()]))

@parsy.generate
def tokenize():
    start = yield separator.many()
    start = sum(start, [])
    token1 = yield token
    start.append(token1)
    tokens = yield (separator.at_least(1).map(lambda x: sum(x,[])) + token.map(singleton)).many()
    tokens = sum(tokens, [])
    endsep = yield separator.many()
    endsep = sum(endsep, [])

    return start + tokens + endsep

@parsy.generate
def basic_tokenize():
    start = yield separator.many()
    start = sum(start, [])
    token1 = yield string
    start.append(token1)
    tokens = yield (separator.at_least(1).map(lambda x: sum(x,[])) + string.map(singleton)).many()
    tokens = sum(tokens, [])
    endsep = yield separator.many()
    endsep = sum(endsep, [])

    return start + tokens + endsep

negate = lambda expr: ((parsy.match_item('-') >> expr.map(Not)) | expr)
wrap = lambda expr: (parsy.match_item('(') >> expr << parsy.match_item(')'))

@parsy.generate
def expr():
    e = yield orExpr
    es = yield (
        parsy.match_item('|') >> orExpr
    ).many()
    for e2 in es:
        e = Maximum(e, e2)
    return parsy.success(e)

@parsy.generate
def orExpr():
    e = yield andExpr
    es = yield (
        parsy.match_item('OR').optional() >> andExpr
    ).many()
    for e2 in es:
        e = Or(e, e2)
    return parsy.success(e)


@parsy.generate
def andExpr():
    e = yield simpleExpr
    es = yield (
        parsy.match_item('AND') >> simpleExpr
    ).many()
    for e2 in es:
        e = And(e, e2)
    return parsy.success(e)


simpleExpr = negate(
    parsy.test_item(is_instance(Expression), 'expression')
  | wrap(expr)
)

@parsy.generate
def simple_parse():
    exprs = yield (
        negate(parsy.test_item(isinstance(Expression), 'expression')).map(singleton) | parsy.test_item(const(True), 'ignore').map(const([]))
    ).many()
    exprs = sum(exprs, [])
    try:
        e = exprs.pop()
        for e2 in exprs:
            e = Or(e, e2)
        return e
    except IndexError as err:
        raise NoExpression from err


class BasicParser:
    def __init__(self, tokens):
        self.tokens = tokens

    @classmethod
    def tokenize(cls, s):
        return cls(basic_tokenize.parse(s))

    def parse(self):
        if len(self.tokens):
            return reduce(And, (CollectionExpr(t) for t in self.tokens))
        else:
            raise NoExpression


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens

    @classmethod
    def tokenize(cls, s):
        try:
            return cls(tokenize.parse(s))
        except parsy.ParseError as err:
            raise NoExpression from err
    def parse(self):
        try:
            return expr.parse(self.tokens)
        except parsy.ParseError as err:
            if ')' in err.expected:
                raise ExpectedParenthesis from err
            elif self.tokens[err.index] == ')':
                raise UnexpectedParenthesis(err.index) from err

    def simple_parse(self):
        return simple_parse.parse(self.tokens)


def parse(s):
    try:
        tokens = tokenize.parse(s)
        return expr.parse(tokens)
    except parsy.ParseError as err:
        if ')' in err.expected:
            raise ExpectedParenthesis from err
        elif tokens[err.index] == ')':
            raise UnexpectedParenthesis(err.index) from err


class UnexpectedParenthesis(BaseException):
    def __init__(self, index):
        self.index = index


class ExpectedParenthesis(BaseException):
    pass

class NoExpression(BaseException):
    pass

@dataclass
class OpenParen:
    def __str__(self):
        return '('
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> parsy.string('(').map(const((cls(), [])))

@dataclass
class CloseParen:
    def __str__(self):
        return ')'
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> parsy.string(')').map(const((cls(), [])))

@dataclass
class NegateSign:
    def __str__(self):
        return '-'
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> parsy.string('-').map(const((cls(), [])))

escaped = (
      parsy.string(r'\\').map(const(('\\', [])))
    | parsy.string(r'\ ').map(const((' ', [])))
    | parsy.string(r'\t').map(const((' ', [])))
    | parsy.string(r'\r').map(const((' ', [])))
    | parsy.string(r'\n').map(const((' ', [])))
    | parsy.string(r'\"').map(const(('"', [])))
    | parsy.string(r'\(').map(const(('(', [])))
    | parsy.string(r'\)').map(const((')', [])))
    | parsy.string(r'\:').map(const((':', [])))
)

schunk = (
      escaped
    | parsy.regex(r'[^\\\s\(\)":]+').map(lambda s: (s, []))
)

qchunk = (
      escaped
    | parsy.regex(r'[^\\"]+').map(lambda s: (s, []))
)

qchunk_unmatched = (
      escaped
    | parsy.regex(r'[^\\]+').map(lambda s: (s, []))
)

@parsy.generate
def quoted2():
    yield parsy.string('"')
    s = yield qchunk.many()
    yield parsy.string('"')
    parts, errors = zip(*s)
    return ''.join(parts), [a for b in errors for a in b]

@parsy.generate
def quoted2_unmatched():
    ((_, c1), s, (_, c2)) = yield (parsy.string('"') >> qchunk_unmatched.many()).mark()
    try:
        parts, errors = zip(*s)
    except ValueError:
        parts = []
        errors = []
    return ''.join(parts), [a for b in errors for a in b] + ['Unmatched quote at index {}'.format(c1+1)]

@parsy.generate
def string2():
    s = yield schunk.at_least(1)
    parts, errors = zip(*s)
    return ''.join(parts), [a for b in errors for a in b]
trans = str.maketrans({
    " ": r"\ ",
    "\\": r"\\",
    "\t": r"\t",
    "\r": r"\r",
    "\n": r"\n",
    "\"": r"\"",
    "(": r"\(",
    ")": r"\)",
    ":": r"\:",
})

@dataclass
class BinaryKeyword:
    value: str
    def __str__(self):
        return self.value

    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> (parsy.string("AND") | parsy.string("OR") | parsy.string("|")).map(lambda s: (cls(s), [])) << parsy.peek(parsy.whitespace)

@dataclass
class SearchTerm:
    value: str
    def __str__(self):
        return self.value.translate(trans)
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> (string2 | quoted2).map(lambda s: (cls(s[0]), s[1]))

@dataclass
class UnmatchedSearchTermQuote:
    value: str

    def __str__(self):
        return '"' + self.value

    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> quoted2_unmatched.map(lambda s: (cls(s[0]), s[1]))

@dataclass
class TypedSearchTerm:
    field: str
    value: str
    def __str__(self):
        return '{field}:{value}'.format(field=self.field, value=self.value.translate(trans))
    @classmethod
    def parser(cls):
        @parsy.generate
        def parse():
            field, errors1 = yield parsy.whitespace.many() >> string2 << parsy.string(":")
            value, errors2 = yield (string2 | quoted2)
            errors = [a for b in errors1 for a in b] + [a for b in errors2 for a in b]
            return cls(field, value), errors
        return parse

@dataclass
class MissingField:
    def __str__(self):
        return ":"
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> parsy.string(":").mark().map(lambda s: (cls(), ['Colon (:) with no field preceding it at index {}'.format(s[0][1]+1)]))

@dataclass
class LoneBackslash:
    def __str__(self):
        return "\\"
    @classmethod
    def parser(cls):
        return parsy.whitespace.many() >> parsy.string("\\").mark().map(lambda s: (cls(), [r'Unescaped \ at index {}'.format(s[0][1]+1)]))

class Lexer:
    def parse(self, s):
        @parsy.generate
        def parser():
            s = yield (OpenParen.parser() | CloseParen.parser() | NegateSign.parser() | BinaryKeyword.parser() | TypedSearchTerm.parser() | SearchTerm.parser() | MissingField.parser() | LoneBackslash.parser() | UnmatchedSearchTermQuote.parser()).many()
            yield parsy.whitespace.many()
            try:
                tokens, errors = zip(*s)
                return list(tokens), [error for a in errors for error in a]
            except ValueError:
                return [], []
        s = parser.parse(s)
        return s

    def format(self, ts):
        fragments = []
        for (i, t) in enumerate(ts):
            if i > 0 and (isinstance(ts[i-1], CloseParen) or isinstance(ts[i-1], SearchTerm) or isinstance(ts[i-1], TypedSearchTerm) or isinstance(ts[i-1], BinaryKeyword)):
                fragments.append(' ')
            fragments.append(str(t))
        return ''.join(fragments)
