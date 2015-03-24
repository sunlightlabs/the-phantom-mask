import requests
import re
from config import settings
from lib import geocoder
from lib import usps
# disable invalid SSL warnings - doesn't matter

def zip4_lookup(street_address, city, state, zip=''):
    # First try usps lookup because it doesn't eat up geolocation credits
    try:
        print "Trying USPS first"
        zip5, zip4 = usps.usps_zip_lookup(street_address, city, state, zip)
        if zip4 is not None: return zip4
    except:
        print "Error scraping from USPS ... moving on to geocoding"

    # If USPS is unable to determine zip4 then use geolocation method
    print "Falling back to geolocation"
    geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
    geo.lookup(street_address=street_address, city=city, state=state, zip5=zip)
    lat,lng = geo.lat_long()
    geo.reverse_lookup(lat,lng)
    try:
        return geo.zip4()
    except: # Give up. User must enter in their zip4 manually.
        return None