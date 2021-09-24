import logging
import ssl
import json
from urllib.request import urlopen, HTTPError
from urllib.parse import urlencode
from time import sleep
from .geom import Location, Bounds
from django.contrib.gis.geos import Point, Polygon, MultiPolygon

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

class GeocodeError(Exception):
    pass

class Geocoder:
    def __init__(self, key, url=GEOCODE_URL, max_attempts=3, pause=2):
        self.key = key
        self.url = url
        self.max_attempts = max_attempts
        self.pause = pause

    def extract_shape(self, data):
        for result in data:
            try:
                geometry = result['geometry']
                location = geometry['location']
                centroid=(location['lng'], location['lat'])
                bounds = geometry['bounds']
                bounds = Bounds(
                    xmin=bounds['southwest']['lng'],
                    ymin=bounds['southwest']['lat'],
                    xmax=bounds['northeast']['lng'],
                    ymax=bounds['northeast']['lat'],
                )
                return Location(
                    centroid=Point(x=centroid[0], y=centroid[1], srid=4326),
                    bounds=MultiPolygon([Polygon.from_bbox(b.astuple()) for b in bounds.as_shifted_bounds()], srid=4326),
                )
            except:
                pass


    def geocode(self, description):
        #ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        logging.debug(description)
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "key": self.key,
            "address": description,
            "sensor": "false",
        }
        signed_url = "{}?{}".format(url, urlencode(params))
        logging.debug(signed_url)
        succeeded = False
        attempts = 0
        data = None
        while not succeeded and attempts < self.max_attempts:
            try:
                data = json.loads(
                    urlopen(signed_url).read().decode("utf-8")
                )
                if data["status"] == "OVER_QUERY_LIMIT":
                    sleep(self.pause)
                else:
                    succeeded = True
            except:
                import sys

                logging.exception("Unexpected error: %s", sys.exc_info()[0])
                sleep(self.pause)
            attempts += 1

        if attempts == self.max_attempts:
            logging.warning("DAILY GOOGLE MAPS RATE LIMIT HIT")
        location = self.extract_shape(data['results'])
        if not location:
            raise GeocodeError(description)
        return location
