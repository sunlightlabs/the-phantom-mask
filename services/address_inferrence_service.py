from lib import usps
from geolocation_service import geolocate, reverse_geolocate


def address_lookup(**kwargs):

    try:
        print 'Trying USPS first...'
        address = usps.usps_address_lookup(**kwargs)
        if address['city'] is not '' and address['state'] is not '':
            return address
        print 'Falling back to geolocation...'
        lat, lng = geolocate(**kwargs)
        return reverse_geolocate(lat, lng).address()
    except:
        return None

def zip4_lookup(street_address, city, state, zip5=''):
    # First try usps lookup because it doesn't eat up geolocation credits
    try:
        print "Trying USPS first"
        zip5, zip4 = usps.usps_zip_lookup(street_address, city, state, zip5)
        if zip4 is not None:
            return zip4
    except:
        print "Error scraping from USPS ... moving on to geocoding"

    # If USPS is unable to determine zip4 then use geolocation method
    print "Falling back to geolocation"
    try:
        lat, lng = geolocate(street_address=street_address, city=city, state=state, zip5=zip5)
        return reverse_geolocate(lat, lng).zip4()
    except: # Give up. User must enter in their zip4 manually.
        return None