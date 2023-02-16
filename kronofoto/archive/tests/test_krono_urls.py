from django.test import tag
#from ..templatetags.krono_url import krono_url
from ..reverse import reverse, resolve
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase, from_model
from hypothesis.provisional import domains
from django.contrib.sites.models import Site
from .util import archives
from urllib.parse import quote

@tag('fast2')
class TestUrls(TestCase):
    @given(from_model(Site, domain=domains()))
    def testRandomImage(self, site):
        namespace = 'kronofoto'
        viewname = 'random-image'
        resolveMatch = resolve(reverse(f'{namespace}:{viewname}', site=site))
        self.assertEqual(site.id, resolveMatch.site.id)
        self.assertEqual(resolveMatch.match.url_name, viewname)
        self.assertEqual(resolveMatch.match.namespace, namespace)

    @given(from_model(Site, domain=domains()), archives().filter(lambda a: len(a.slug) > 0))
    def testRandomImage(self, site, archive):
        namespace = 'kronofoto'
        viewname = 'random-image'
        kwargs = {'short_name': archive.slug}
        resolveMatch = resolve(reverse(f'{namespace}:{viewname}', kwargs=kwargs, site=site))
        self.assertEqual(site.id, resolveMatch.site.id)
        self.assertEqual(resolveMatch.match.url_name, viewname)
        self.assertEqual(resolveMatch.match.namespace, namespace)
        self.assertEqual(resolveMatch.match.kwargs['short_name'], kwargs['short_name'])
