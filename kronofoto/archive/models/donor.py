from django.db import models
from django.db.models import Count
from .collectible import Collectible
from .archive import Archive

class DonorQuerySet(models.QuerySet):
    def annotate_scannedcount(self):
        return self.annotate(scanned_count=Count('photos_scanned'))

    def annotate_donatedcount(self):
        return self.annotate(donated_count=Count('photo'))

    def filter_donated(self, at_least=1):
        return self.annotate_donatedcount().filter(donated_count__gte=at_least)

class Donor(Collectible, models.Model):
    last_name = models.CharField(max_length=256, blank=True)
    first_name = models.CharField(max_length=256, blank=True)
    archive = models.ForeignKey(Archive, models.PROTECT, null=False)
    home_phone = models.CharField(max_length=256, blank=True)
    street1 = models.CharField(max_length=256, blank=True)
    street2 = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=256, blank=True)
    state = models.CharField(max_length=256, blank=True)
    zip = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=256, blank=True)
    objects = DonorQuerySet.as_manager()

    class Meta:
        ordering = ('last_name', 'first_name')
        index_together = ('last_name', 'first_name')

    def display_format(self):
        return '{first} {last}'.format(first=self.first_name, last=self.last_name) if self.first_name else self.last_name

    def __str__(self):
        return '{last}, {first}'.format(first=self.first_name, last=self.last_name) if self.first_name else self.last_name

    def encode_params(self, params):
        params['donor'] = self.id
        return params.urlencode()

    @staticmethod
    def index():
        return [
            {'name': '{last}, {first}'.format(last=donor.last_name, first=donor.first_name), 'count': donor.count, 'href': donor.get_absolute_url()}
            for donor in Donor.objects.annotate(count=Count('photo__id')).order_by('last_name', 'first_name').filter(count__gt=0)
        ]
