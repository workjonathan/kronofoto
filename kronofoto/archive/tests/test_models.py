from django.test import TestCase, tag
from django.urls import reverse
from django.utils.http import urlencode
from ..models import Donor, Term
from ..models.archive import Archive

@tag("fast")
class DonorTest(TestCase):
    def testURL(self):
        donor = Donor.objects.create(
            last_name='last',
            first_name='first',
            archive=Archive.objects.all()[0],
        )
        self.assertEqual(donor.get_absolute_url(), "{}?{}".format(reverse('kronofoto:gridview'), urlencode({'donor': donor.id})))

@tag("fast")
class TermTest(TestCase):
    def testURL(self):
        term = Term.objects.create(term="test term")
        self.assertEqual(term.get_absolute_url(), "{}?{}".format(reverse('kronofoto:gridview'), urlencode({'term': term.id})))
