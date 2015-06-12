from config import settings
from lib import geocoder


def geolocate(**kwargs):
    geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
    geo.lookup(**kwargs)
    return geo.lat_long()


def reverse_geolocate(lat, lng):
    geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
    return geo.reverse_lookup(lat, lng)