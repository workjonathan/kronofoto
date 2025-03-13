from __future__ import annotations
from django.db import models
from django.db.models import Count, QuerySet
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Exists, OuterRef, F, Subquery, Func
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse
from .collectible import Collectible
from .archive import Archive, RemoteActor
from typing_extensions import Self
from typing import final, Any, Type, List, Dict, Literal, TYPE_CHECKING
#from .activity_dicts import ActivitypubContact, DonorValue


class DonorQuerySet(models.QuerySet):
    pass


class Donor(Collectible, models.Model):
    archive = models.ForeignKey(Archive, on_delete=models.PROTECT, null=False)
    last_name = models.CharField(max_length=257, blank=True)
    first_name = models.CharField(max_length=256, blank=True)
    email = models.EmailField(blank=True)
    home_phone = models.CharField(max_length=256, blank=True)
    street1 = models.CharField(max_length=256, blank=True)
    street2 = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=256, blank=True)
    state = models.CharField(max_length=256, blank=True)
    zip = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=256, blank=True)

    objects = DonorQuerySet.as_manager()

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = (models.Index(fields=["last_name", "first_name"]),)

    def display_format(self) -> str:
        return (
            "{first} {last}".format(first=self.first_name, last=self.last_name)
            if self.first_name
            else self.last_name
        )

    def is_owned_by(self, actor: RemoteActor) -> bool:
        return self.archive.actor is not None and self.archive.actor.id == actor.id

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return (
                "{last}, {first}".format(first=self.first_name, last=self.last_name)
                if self.first_name
                else self.last_name
            )
        return "Unnamed contributor"

    def encode_params(self, params: Any) -> Any:
        params["donor"] = self.id
        return params.urlencode()
