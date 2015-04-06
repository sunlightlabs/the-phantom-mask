from config import settings
from lib import geocoder


def geolocate(street_address, city, state, zip5):
    geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
    geo.lookup(street_address=street_address, city=city, state=state, zip5=zip5)
    return geo.lat_long()


def reverse_geolocate(lat, lng):
    geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
    return geo.reverse_lookup(lat, lng)