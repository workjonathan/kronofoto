from django.contrib.sitemaps import Sitemap
from fortepan_us.kronofoto import models
from django.urls import reverse
from django.db.models import QuerySet

class PhotoSiteMap(Sitemap):
    protocol = "https"
    def items(self) -> models.PhotoQuerySet:
        return models.Photo.objects.filter(is_published=True)

    def location(self, photo: models.Photo) -> str:
        return reverse('kronofoto:photoview', kwargs={"photo": photo.id})

class TagSiteMap(Sitemap):
    protocol = "https"
    def items(self) -> QuerySet:
        return models.Tag.objects.all()

    def location(self, obj: models.Tag) -> str:
        return "{}?tag={}".format(reverse('kronofoto:gridview'), obj.tag)

class TermSiteMap(Sitemap):
    protocol = "https"
    def items(self) -> QuerySet:
        return models.Term.objects.all()

    def location(self, obj: models.Term) -> str:
        return "{}?term={}".format(reverse('kronofoto:gridview'), obj.id)

class DonorSiteMap(Sitemap):
    protocol = "https"
    def items(self) -> QuerySet:
        return models.Donor.objects.all()

    def location(self, obj: models.Donor) -> str:
        return "{}?donor={}".format(reverse('kronofoto:gridview'), obj.id)
