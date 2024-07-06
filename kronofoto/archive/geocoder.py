from django.conf import settings
from .models import CSVRecord, Location, Photo
from geocoding import geom
from geocoding.google import Geocoder, GeocodeError
import logging
from typing import Any, Optional, Union, Dict, List, Protocol

class GeocoderProtocol(Protocol):
    def geocode(self, description: str) -> Any:
        pass

class CachingGeocoder:
    def __init__(self, geocoder: GeocoderProtocol):
        self.geocoder = geocoder

    def geocode(self, description: str) -> geom.Location:
        try:
            location: Any = Location.objects.locate(description=description)
            return geom.Location(centroid=location.location_point, bounds=location.location_bounds)
        except Location.DoesNotExist:
            location = self.geocoder.geocode(description=description)
            Location.objects.create(
                description=description,
                location_point=location.centroid,
                location_bounds=location.bounds,
            )
            return location



class CSVGeocoder:
    def __init__(self, geocoder: GeocoderProtocol=CachingGeocoder(geocoder=Geocoder(key=settings.GOOGLE_MAPS_KEY))):
        self.geocoder = geocoder

    def geocode_from_csv_data(self) -> None:
        for photo in Photo.objects.exclude_geocoded():
            try:
                description = photo.location(with_address=True, force_country=True)
                description = description.strip()
                if description and description != 'Location: n/a':
                    location = self.geocoder.geocode(description=description)
                    photo.location_from_google = True
                    photo.location_point = location.centroid
                    photo.location_bounds = location.bounds
                    photo.save()
            except GeocodeError:
                logging.exception('geocoding error on {}'.format(photo.id))
