import sunlight
from config import settings
from geolocation_service import geolocate, reverse_geolocate

def determine_district(**kwargs):
    sunlight.config.API_KEY = settings.SUNLIGHT_API_KEY

    if kwargs.has_key('latitude') and kwargs.has_key('longitude'):
        data = sunlight.congress.locate_districts_by_lat_lon(kwargs.get('latitude'),kwargs.get('longitude'))
    elif kwargs.has_key('zip5'):
        data = sunlight.congress.locate_districts_by_zip(kwargs.get('zip5'))
        if data.count > 1 and kwargs.get('street_address') and kwargs.get('city') and kwargs.get('state'):
            lat, lng = geolocate(street_address=kwargs.get('street_address'),
                                 city=kwargs.get('city'),
                                 state=kwargs.get('state'),
                                 zip5=kwargs.get('zip5'))
            data = sunlight.congress.locate_districts_by_lat_lon(lat,lng)
    else:
        raise KeyError('Must provide appropriate keyword arguments')

    return data[0]['district']