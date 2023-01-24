from django.test import SimpleTestCase, tag
from django.db.models import Q
from archive import models
from django.contrib.auth.models import AnonymousUser
from hypothesis.extra.django import TestCase
from hypothesis import given, strategies
from archive.search import expression, evaluate, parser
from archive.search.parser import Lexer, OpenParen, SearchTerm, UnmatchedSearchTermQuote, TypedSearchTerm, MissingField
from archive.search.expression import (
    And, CollectionExpr, Maximum, Tag, Term, City, State, Country, County, Caption, Or, Not, Donor, YearEquals, YearLTE, YearGTE, Description, TagExactly, TermExactly, DonorExactly
)

@strategies.composite
def tokens(draw):
    type = draw(strategies.integers(min_value=0, max_value=6))
    if type == 0:
        return '-'
    if type == 1:
        return '('
    if type == 2:
        return ')'
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if type == 3:
        return draw(strategies.text(alphabet=alphabet))
    if type == 4:
        return '"{}"'.format(draw(strategies.text(alphabet=alphabet + ' ')))
    if type == 5:
        return '{}:{}'.format(draw(strategies.text(alphabet=alphabet, min_size=1)), draw(strategies.text(alphabet=alphabet)))
    if type == 6:
        return '{}:"{}"'.format(draw(strategies.text(alphabet=alphabet, min_size=1)), draw(strategies.text(alphabet=alphabet + ' ')))

class AutocompleteParserTest(TestCase):
    def testBasics(self):
        lexer = Lexer()
        self.assertEqual(tuple(lexer.parse("(")), ([OpenParen()], []))
        self.assertEqual(tuple(lexer.parse("asdf\\ fdsa")), ([SearchTerm("asdf fdsa")], []))
        self.assertEqual(tuple(lexer.parse('"asdf fdsa"')), ([SearchTerm("asdf fdsa")], []))
        self.assertEqual(tuple(lexer.parse(' ')), ([], []))
        self.assertEqual(tuple(lexer.parse('tag:test')), ([TypedSearchTerm('tag', 'test')], []))
        self.assertEqual(tuple(lexer.parse('"')), ([UnmatchedSearchTermQuote('')], ["Unmatched quote at index 1"]))
        self.assertEqual(tuple(lexer.parse(':')), ([MissingField()], ["Colon (:) with no field preceding it at index 1"]))
    @given(strategies.text(min_size=1))
    def testParseEveryInput(self, input):
        "Lexer should be able to convert any string to a list of tokens and a list of tokens to a string."
        "All whitespace should be replaced by a single space, so string -> ([tokens], [errors]) -> string may fail."
        "However, string -> ([tokens], [errors]) -> string -> ([tokens], [errors]) should produce identical tokens."
        lexer = Lexer()
        tokens, errors = lexer.parse(input)
        tokens2, errors2 = lexer.parse(lexer.format(tokens))
        self.assertEqual(tokens, tokens2)
    #@given(strategies.lists(tokens()))
    #def testFail(self, t):
    #    self.assertFalse(t)

@tag("fast")
class BasicParserTest(SimpleTestCase):
    def testParserShouldProduceCollectionExpressions(self):
        expr = parser.BasicParser.tokenize("dog").parse()
        self.assertTrue(expr.is_collection())

    def testParserShouldAcceptSimpleWords(self):
        expr = parser.BasicParser.tokenize("dog").parse()
        self.assertEqual(expr, Maximum(Tag('dog'), Maximum(Term('dog'), Maximum(City('dog'), Maximum(State('dog'), Maximum(Country('dog'), County('dog')))))))

    def testParserShouldCombineTerms(self):
        expr = parser.BasicParser.tokenize("dog waterloo").parse()
        self.assertEqual(expr, And(CollectionExpr('dog'), CollectionExpr('waterloo')))


@tag("fast")
class ParserTest(SimpleTestCase):
    def testParserShouldParseTypedNumbers(self):
        self.assertEqual(parser.tokenize.parse('year:1912'), [YearEquals(1912)])
        self.assertEqual(parser.parse('year:1912'), YearEquals(1912))

    def testParserShouldParseTypedStrings(self):
        self.assertEqual(parser.tokenize.parse('caption:dog'), [Caption('dog')])
        self.assertEqual(parser.parse('caption:dog'), Caption('dog'))

    def testParserShouldParseUntypedStrings(self):
        self.assertEqual(
            parser.tokenize.parse('dog'),
            [Or(Donor('dog'), Or(Caption('dog'), Or(State('dog'), Or(Country('dog'), Or(County('dog'), Or(City('dog'), Or(Tag('dog'), Term('dog'))))))))],
        )
        self.assertEqual(
            parser.parse('dog'),
            Or(Donor('dog'), Or(Caption('dog'), Or(State('dog'), Or(Country('dog'), Or(County('dog'), Or(City('dog'), Or(Tag('dog'), Term('dog')))))))),
        )

    def testParserShouldParseUntypedNumbers(self):
        self.assertEqual(parser.tokenize.parse('1912'), [Or(YearEquals(1912), Or(Donor('1912'), Or(Caption('1912'), Or(State('1912'), Or(Country('1912'), Or(County('1912'), Or(City('1912'), Or(Tag('1912'), Term('1912')))))))))])
        self.assertEqual(parser.parse('1912'), Or(YearEquals(1912), Or(Donor('1912'), Or(Caption('1912'), Or(State('1912'), Or(Country('1912'), Or(County('1912'), Or(City('1912'), Or(Tag('1912'), Term('1912'))))))))))

    def testParserShouldNegateTerms(self):
        self.assertEqual(parser.tokenize.parse('-caption:dog'), ['-', Caption('dog')])
        self.assertEqual(parser.parse('-caption:dog'), Not(Caption('dog')))

    def testParserShouldParseAndExpressions(self):
        self.assertEqual(parser.tokenize.parse('caption:dog AND caption:cat'), [Caption('dog'), 'AND', Caption('cat')])
        self.assertEqual(parser.parse('caption:dog AND caption:cat'), And(Caption('dog'), Caption('cat')))

    def testParserShouldParseOrExpressions(self):
        self.assertEqual(parser.tokenize.parse('caption:dog OR caption:cat'), [Caption('dog'), 'OR', Caption('cat')])
        self.assertEqual(parser.parse('caption:dog OR caption:cat'), Or(Caption('dog'), Caption('cat')))

    def testParserShouldSupportOrderOfOperations(self):
        self.assertEqual(
            parser.tokenize.parse('caption:bird OR caption:dog | caption:cat OR caption:banana'),
            [Caption('bird'), 'OR', Caption('dog'), '|', Caption('cat'), 'OR', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird OR caption:dog | caption:cat OR caption:banana'),
            Maximum(Or(Caption('bird'), Caption('dog')), Or(Caption('cat'), Caption('banana'))),
        )
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            [Caption('bird'), 'AND', Caption('dog'), 'OR', Caption('cat'), 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            Or(And(Caption('bird'), Caption('dog')), And(Caption('cat'), Caption('banana'))),
        )
        self.assertEqual(
            parser.tokenize.parse('-caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            ['-', Caption('bird'), 'AND', Caption('dog'), 'OR', Caption('cat'), 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('-caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            Or(And(Not(Caption('bird')), Caption('dog')), And(Caption('cat'), Caption('banana'))),
        )

    def testParserShouldSupportParentheses(self):
        self.assertEqual(parser.tokenize.parse('(caption:bird)'), ['(', Caption('bird'), ')'])
        self.assertEqual(parser.parse('(caption:bird)'), Caption('bird'))
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND (caption:dog OR caption:cat) AND caption:banana'),
            [Caption('bird'), 'AND', '(', Caption('dog'), 'OR', Caption('cat'), ')', 'AND', Caption('banana')]
        )
        self.assertEqual(
            parser.parse('caption:bird AND (caption:dog OR caption:cat) AND caption:banana'),
            And(And(Caption('bird'), Or(Caption('dog'), Caption('cat'))), Caption('banana')),
        )
        self.assertEqual(
            parser.tokenize.parse('(caption:bird OR caption:dog) AND (caption:cat OR caption:banana)'),
            ['(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse('(caption:bird OR caption:dog) AND (caption:cat OR caption:banana)'),
            And(Or(Caption('bird'), Caption('dog')), Or(Caption('cat'), Caption('banana'))),
        )
        self.assertEqual(
            parser.tokenize.parse('((caption:bird OR caption:dog) AND (caption:cat caption:banana))'),
            ['(', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', Caption('cat'), Caption('banana'), ')', ')'],
        )
        self.assertEqual(
            parser.parse('((caption:bird OR caption:dog) AND (caption:cat caption:banana))'),
            And(Or(Caption('bird'), Caption('dog')), Or(Caption('cat'), Caption('banana'))),
        )

    def testParserShouldSupportNegatedParentheses(self):
        self.assertEqual(parser.tokenize.parse('-(caption:bird)'), ['-', '(', Caption('bird'), ')'])
        self.assertEqual(parser.parse('-(caption:bird)'), Not(Caption('bird')))
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND -(caption:dog OR caption:cat) AND caption:banana'),
            [Caption('bird'), 'AND', '-', '(', Caption('dog'), 'OR', Caption('cat'), ')', 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird AND -(caption:dog OR caption:cat) AND caption:banana'),
            And(And(Caption('bird'), Not(Or(Caption('dog'), Caption('cat')))), Caption('banana')),
        )
        self.assertEqual(
            parser.tokenize.parse('-(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)'),
            ['-', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', '-', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse('-(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)'),
            And(Not(Or(Caption('bird'), Caption('dog'))), Or(Not(Caption('cat')), Caption('banana'))),
        )

    def testParserShouldNotTripOverExtraneousSpacesAndRandomStuff(self):
        self.assertEqual(parser.tokenize.parse('((caption:bird))'), ['(', '(', Caption('bird'), ')', ')'])
        self.assertEqual(parser.parse('((caption:bird))'), Caption('bird'))
        self.assertEqual(
            parser.tokenize.parse(' -( caption:bird OR caption:dog  )AND(- caption:cat OR caption:banana) '),
            ['-', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', '-', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse(' -( caption:bird OR caption:dog  )AND(- caption:cat OR caption:banana) '),
            And(Not(Or(Caption('bird'), Caption('dog'))), Or(Not(Caption('cat')), Caption('banana'))),
        )

    def testParserShouldNotDieDueToUnmatchedParens(self):
        with self.assertRaises(parser.UnexpectedParenthesis) as cm:
            parser.parse('caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)')
        self.assertEqual(cm.exception.index, 3)

        with self.assertRaises(parser.ExpectedParenthesis):
            parser.parse('(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana')

        with self.assertRaises(parser.UnexpectedParenthesis):
            parser.parse('() AND (-caption:cat OR caption:banana')


@tag("fast")
class ExpressionTest(TestCase):
    @given(strategies.integers())
    def testShouldSupportNegation(self, year):
        q = (~YearEquals(year)).buildQ(user=AnonymousUser())
        self.assertEqual(q, ~Q(year=year))

    @given(strategies.integers(), strategies.integers())
    def testShouldSupportBooleanAnd(self, year1, year2):
        q = (YearEquals(year1) & YearEquals(year2)).buildQ(user=AnonymousUser())
        self.assertEqual(q, Q(year=year1) & Q(year=year2))

    @given(strategies.integers(), strategies.integers())
    def testShouldSupportBooleanOr(self, year1, year2):
        q = (YearEquals(year1) | YearEquals(year2)).buildQ(user=AnonymousUser())
        self.assertEqual(q, Q(year=year1) | Q(year=year2))

@tag("fast")
class ExpressionTest(SimpleTestCase):
    def testThingsAreCollections(self):
        self.assertTrue(YearEquals(1912).is_collection())
        self.assertTrue(YearLTE(1912).is_collection())
        self.assertTrue(YearGTE(1912).is_collection())
        self.assertTrue(City("Waterloo").is_collection())
        self.assertTrue(County("Black Hawk").is_collection())
        self.assertTrue(State("IA").is_collection())
        self.assertTrue(Country("USA").is_collection())
        self.assertTrue(Term("Farm").is_collection())

    def testMaximumCanBeCollection(self):
        self.assertTrue(Maximum(Term("Farm"), Term("Animals")).is_collection())
        self.assertFalse(Maximum(Term("Farm"), Caption("Animals")).is_collection())

    def testAndCanBeCollection(self):
        self.assertTrue(And(Term("Farm"), Term("Animals")).is_collection())
        self.assertFalse(And(Term("Farm"), Caption("Animals")).is_collection())

    def testOrIsNotCollection(self):
        self.assertFalse(Or(Term("Farm"), Term("Animals")).is_collection())

    def testHasDescription(self):
        self.assertEqual(YearEquals(1912).description(), Description([YearEquals(1912)]))
        self.assertEqual(YearLTE(1912).description(), Description([YearLTE(1912)]))
        self.assertEqual(YearGTE(1912).description(), Description([YearGTE(1912)]))
        self.assertEqual(City("Waterloo").description(), Description([City("Waterloo")]))
        self.assertEqual(County("Black Hawk").description(), Description([County("Black Hawk")]))
        self.assertEqual(State("IA").description(), Description([State("IA")]))
        self.assertEqual(Country("USA").description(), Description([Country("USA")]))
        self.assertEqual(Term("Farm").description(), Description([Term("Farm")]))
        self.assertEqual((Term("dog") & Term("Farm")).description(), Description([Term("dog"), Term("Farm")]))
        self.assertEqual((Maximum(Term("dog"), Term("dog"))).description(), Description([Maximum(Term("dog"), Term("dog"))]))

    def testShortLabels(self):
        self.assertEqual(YearEquals(1912).short_label(), "Year: 1912")
        self.assertEqual(YearLTE(1912).short_label(), "Year: 1912-")
        self.assertEqual(YearGTE(1912).short_label(), "Year: 1912+")
        self.assertEqual(City("Waterloo").short_label(), "City: Waterloo")
        self.assertEqual(County("Black Hawk").short_label(), "County: Black Hawk")
        self.assertEqual(State("IA").short_label(), "State: IA")
        self.assertEqual(Country("USA").short_label(), "Country: USA")
        self.assertEqual(Term("Farm").short_label(), "Term: farm")
        with self.assertRaises(NotImplementedError):
            (Term("dog") & Term("Farm")).short_label()
        self.assertEqual((Maximum(Term("dog"), Term("dog"))).short_label(), "dog")

    def testGroupLabels(self):
        self.assertEqual(YearEquals(1912).group(), "year")
        self.assertEqual(YearLTE(1912).group(), "year")
        self.assertEqual(YearGTE(1912).group(), "year")
        self.assertEqual(City("Waterloo").group(), "location")
        self.assertEqual(County("Black Hawk").group(), "location")
        self.assertEqual(State("IA").group(), "location")
        self.assertEqual(Country("USA").group(), "location")
        self.assertEqual(Term("Farm").group(), "term")
        with self.assertRaises(NotImplementedError):
            (Term("dog") & Term("Farm")).group()
        self.assertEqual((Maximum(Term("dog"), Term("dog"))).group(), "max")


@tag("fast")
class DescriptionTest(SimpleTestCase):
    def testHasLongDescription(self):
        self.assertEqual(str(Description([Term("dog"), Term("Farm"), YearEquals(1912)])), "from 1912; and termed with dog and farm")
        self.assertEqual(str(Description([YearLTE(1920), YearGTE(1910)])), "between 1910 and 1920")
        self.assertEqual(str(Description([Term("dog"), YearLTE(1920), YearGTE(1910)])), "between 1910 and 1920; and termed with dog")


@tag("fast")
class CollectionQueryTest(TestCase):
    @given(strategies.text(min_size=1), strategies.text(min_size=1))
    def testShouldDescribeCounty(self, place, state):
        coll = models.CollectionQuery(County(place) & State(state), AnonymousUser)
        self.assertEqual(str(coll), 'from {} County, {}'.format(place, state))

    @given(strategies.text(min_size=1), strategies.text(min_size=1))
    def testShouldDescribeCity(self, citytown, state):
        coll = models.CollectionQuery(City(citytown) & State(state), AnonymousUser)
        self.assertEqual(str(coll), 'from {}, {}'.format(citytown, state))

    @given(strategies.text())
    def testShouldDescribeTag(self, s):
        tag = models.Tag(tag=s)
        coll = models.CollectionQuery(TagExactly(tag.tag), AnonymousUser)
        self.assertEqual(str(coll), 'tagged with {}'.format(s))

    @given(strategies.text())
    def testShouldDescribeTerm(self, s):
        term = models.Term(term=s)
        coll = models.CollectionQuery(TermExactly(term), AnonymousUser)
        self.assertEqual(str(coll), 'termed with {}'.format(s))

    @given(strategies.text(), strategies.text())
    def testShouldDescribeDonor(self, first, last):
        donor = models.Donor(first_name=first, last_name=last)
        coll = models.CollectionQuery(DonorExactly(donor), AnonymousUser)
        self.assertEqual(str(coll), 'contributed by {}'.format(donor.display_format()))
