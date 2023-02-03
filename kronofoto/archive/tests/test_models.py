from django.test import TestCase, tag
from django.urls import reverse
from django.utils.http import urlencode
from ..models import Donor, Term

@tag("fast")
class DonorTest(TestCase):
    def testURL(self):
        donor = Donor.objects.create(
            last_name='last',
            first_name='first',
        )
        self.assertEqual(donor.get_absolute_url(), "{}?{}".format(reverse('kronofoto:search-results'), urlencode({'donor': donor.id})))

@tag("fast")
class TermTest(TestCase):
    def testURL(self):
        term = Term.objects.create(term="test term")
        self.assertEqual(term.get_absolute_url(), "{}?{}".format(reverse('kronofoto:search-results'), urlencode({'term': term.id})))
