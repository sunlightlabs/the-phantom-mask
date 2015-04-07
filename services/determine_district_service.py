import sunlight
from config import settings
from geolocation_service import geolocate

def determine_district(**kwargs):
    sunlight.config.API_KEY = settings.SUNLIGHT_API_KEY

    if {'latitude', 'longitude'}.issubset(set(kwargs)):
        data = sunlight.congress.locate_districts_by_lat_lon(kwargs.get('latitude'), kwargs.get('longitude'))
    elif 'zip5' in kwargs:
        data = sunlight.congress.locate_districts_by_zip(kwargs.get('zip5'))
        if data.count > 1 and {'street_address', 'city', 'state'}.issubset(set(kwargs)):
            lat, lng = geolocate(street_address=kwargs.get('street_address'),
                                 city=kwargs.get('city'),
                                 state=kwargs.get('state'),
                                 zip5=kwargs.get('zip5'))
            data = sunlight.congress.locate_districts_by_lat_lon(lat,lng)
        else:
            return None
    else:
        raise KeyError('Must provide appropriate keyword arguments')

    return data[0]['district']