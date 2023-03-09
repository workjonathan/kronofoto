from django.db import models

class ConnecticutRecordQuerySet(models.QuerySet):
    pass

class ConnecticutRecord(models.Model):
    file_id1 = models.IntegerField(null=False)
    file_id2 = models.IntegerField(null=False)
    title = models.TextField(null=False)
    year = models.TextField(null=False)
    contributor = models.TextField(null=False)
    description = models.TextField(null=False)
    location = models.TextField(null=False)

    photo = models.OneToOneField('Photo', on_delete=models.SET_NULL, null=True, unique=True, blank=True)

    objects = ConnecticutRecordQuerySet.as_manager()
    def __str__(self):
        return '{}:{}'.format(self.file_id1, self.file_id2)

    class Meta:
        indexes = [
            models.Index(fields=['file_id1', 'file_id2']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['file_id1', 'file_id2'], name='unique_id_combo'),
        ]




class CSVRecordQuerySet(models.QuerySet):
    def bulk_clean(self):
        records = list(self.all())
        for record in records:
            record.clean_whitespace()
        self.bulk_update(
            records,
            [
                'donorFirstName',
                'donorLastName',
                'scanner',
                'photographer',
                'address',
                'city',
                'county',
                'state',
                'country',
                'comments',
            ],
        )

    def exclude_geocoded(self):
        return self.filter(photo__isnull=False, photo__location_point__isnull=True)

class CSVRecord(models.Model):
    filename = models.TextField(unique=True)
    # unique constraint seems to make sense to me, but there are quite a few
    # duplicate records. should both be added? Or should we take newer added to
    # archive date to be the true record? Or should this be resolved on a case
    # by case basis?
    donorFirstName = models.TextField()
    donorLastName = models.TextField()
    year = models.IntegerField(null=True)
    circa = models.BooleanField(null=True)
    scanner = models.TextField()
    photographer = models.TextField()
    address = models.TextField()
    city = models.TextField()
    county = models.TextField()
    state = models.TextField()
    country = models.TextField()
    comments = models.TextField()
    added_to_archive = models.DateField()
    photo = models.OneToOneField('Photo', on_delete=models.SET_NULL, null=True)

    objects = CSVRecordQuerySet.as_manager()

    def location(self):
        components = []
        if self.country:
            components.append(self.country)
        if self.state:
            components.append(self.state)
        if self.city:
            components.append(self.city)
        elif self.county:
            components.append(self.county)
        if self.address:
            components.append(self.address)
        return ' '.join(reversed(components))


    def clean_whitespace(self):
        self.donorFirstName = self.donorFirstName.strip()
        self.donorLastName = self.donorLastName.strip()
        self.scanner = self.scanner.strip()
        self.photographer = self.photographer.strip()
        self.address = self.address.strip()
        self.city = self.city.strip()
        self.county = self.county.strip()
        self.country = self.country.strip()
        self.state = self.state.strip()
        self.comments = self.comments.strip()
