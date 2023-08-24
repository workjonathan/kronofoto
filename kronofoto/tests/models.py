from django.db import models
from django.contrib.auth.models import User

class UserAgreement(models.Model):
    version = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    agreement = models.ForeignKey("Agreement", on_delete=models.CASCADE)

class Agreement(models.Model):
    version = models.IntegerField(default=0)
    users = models.ManyToManyField(User, through=UserAgreement)
