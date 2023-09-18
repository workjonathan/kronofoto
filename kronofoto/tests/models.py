from django.db import models
from django.contrib.auth.models import User
from archive.models.donor import DonorQuerySet

class UserAgreement(models.Model):
    version = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    agreement = models.ForeignKey("Agreement", on_delete=models.CASCADE)

class Agreement(models.Model):
    version = models.IntegerField(default=0)
    users = models.ManyToManyField(User, through=UserAgreement)


class FakeDonor(models.Model):
    x = models.IntegerField()
    objects = DonorQuerySet.as_manager()

class FakePhoto(models.Model):
    x = models.IntegerField()
    donor = models.ForeignKey(FakeDonor, models.PROTECT, null=True, related_name="photo")
    scanner = models.ForeignKey(
        FakeDonor, null=True, on_delete=models.SET_NULL, blank=True, related_name="archive_photo_scanned"
    )
    def __str__(self):
        return str(self.pk)
