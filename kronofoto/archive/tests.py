from django.test import TestCase
from . import models


class PhotosExist(TestCase):
    def setUp(self):
        coll = models.Collection(
            name="collection",
            displayed_donors="donors",
            year_min=1900,
            year_max=1910,
            total_photos=100,
            is_published=True,
        )

        coll.save()
        photo = models.Photo(
            accession_number="photo1",
            collection=coll,
            city="city1",
            county="county1",
            state="IA",
            country="US",
            year=1901,
            caption="caption1",
            is_featured=True,
            is_published=True,
        )
        photo.save()
        photo = models.Photo(
            accession_number="photo2",
            collection=coll,
            city="city1",
            county="county1",
            state="IA",
            country="US",
            year=1901,
            caption="caption1",
            is_featured=False,
            is_published=False,
        )
        photo.save()
        photo = models.Photo(
            accession_number="photo3",
            collection=coll,
            city="city1",
            county="county1",
            state="IA",
            country="US",
            year=1901,
            caption="caption1",
            is_featured=True,
            is_published=True,
        )
        photo.save()
        photo = models.Photo(
            accession_number="photo4",
            collection=coll,
            city="city2",
            county="county2",
            state="IA",
            country="US",
            year=1901,
            caption="caption1",
            is_featured=True,
            is_published=True,
        )
        photo.save()

    def test_citylisting(self):
        print(models.Photo.objects.values("city"))
