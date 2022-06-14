from django.conf import settings
from .models import CSVRecord
from geocoding.google import Geocoder, GeocodeError
import logging

class CSVGeocoder:
    def __init__(self, geocoder=Geocoder(key=settings.GOOGLE_MAPS_KEY)):
        self.geocoder = geocoder

    def geocode_from_csv_data(self):
        for record in CSVRecord.objects.exclude_geocoded():
            try:
                description = record.location()
                if description.strip():
                    location = self.geocoder.geocode(description=description)
                    photo = record.photo
                    photo.location_point = location.centroid
                    photo.location_bounds = location.bounds
                    photo.save()
            except GeocodeError:
                logging.exception('geocoding error')
