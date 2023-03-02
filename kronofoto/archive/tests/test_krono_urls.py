from django.test import tag, SimpleTestCase, RequestFactory
from ..reverse import reverse, resolve
from hypothesis import given, note
from hypothesis import strategies as st, settings
from hypothesis.extra.django import TestCase, from_model
#from unittest import TestCase
from hypothesis.provisional import domains
from django.utils.text import slugify
from ..templatetags.krono_urls import krono_url, krono_params

@tag('newtests')
class TestUrls(TestCase):

    @settings(max_examples=10)
    @given(domains(), st.text(min_size=1).map(slugify).filter(lambda a: len(a) > 0))
    def testGridViewFromArchive(self, domain, archive):
        namespace = 'kronofoto'
        viewname = 'gridview'
        kwargs = {'short_name': archive}
        resolveMatch = resolve(reverse(f'{namespace}:{viewname}', kwargs=kwargs, domain=domain))
        self.assertEqual(domain, resolveMatch.domain)
        self.assertEqual(resolveMatch.match.url_name, viewname)
        self.assertEqual(resolveMatch.match.namespace, namespace)
        self.assertEqual(resolveMatch.match.kwargs['short_name'], kwargs['short_name'])

    @settings(max_examples=10)
    @given(st.text(min_size=1).map(slugify).filter(lambda a: len(a) > 0))
    def testKronoUrl(self, archive):
        namespace = 'kronofoto'
        viewname = 'gridview'
        kwargs = {'short_name': archive}
        resolveMatch = resolve(krono_url(f'{namespace}:{viewname}', kwargs))
        self.assertEqual(resolveMatch.match.url_name, viewname)
        self.assertEqual(resolveMatch.match.namespace, namespace)
        self.assertEqual(resolveMatch.match.kwargs['short_name'], kwargs['short_name'])
        resolveMatch = resolve(krono_url(f'{namespace}:{viewname}', short_name=kwargs['short_name']))
        self.assertEqual(resolveMatch.match.url_name, viewname)
        self.assertEqual(resolveMatch.match.namespace, namespace)
        self.assertEqual(resolveMatch.match.kwargs['short_name'], kwargs['short_name'])

    @given(st.dictionaries(keys=st.text(min_size=1), values=st.text(min_size=1)))
    def testKronoParams(self, params):
        request = RequestFactory().get('/photos' + krono_params(params))
        for param in params:
            self.assertIn(param, request.GET)
            self.assertEqual(params[param], request.GET[param])

        request = RequestFactory().get('/photos' + krono_params(**params))
        for param in params:
            self.assertIn(param, request.GET)
            self.assertEqual(params[param], request.GET[param])

