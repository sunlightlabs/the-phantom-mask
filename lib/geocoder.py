from inflection import camelize
import requests


class Geocoder():

    def __init__(self, service, opts=None):
        for s in [service, camelize(service)]:
            try: self.service = getattr(self, s)(opts)
            except: continue
        if self.service is None:
            raise AttributeError

    def lookup(self, **params):
        self.service.lookup(**params)

    def reverse_lookup(self, lat, lng):
        self.service.reverse_lookup(lat, lng)

    def check_for_data(self):
        func = self

        def check_for_data_and_call(self, *args, **kwargs):
            if self.service.data is None:
                raise Exception('No data available. Do a lookup or reverse lookup first.')
            return func(self, *args, **kwargs)

        return check_for_data_and_call

    @check_for_data
    def lat_long(self):
        return self.service.lat_long()

    @check_for_data
    def street_address(self):
        return self.service.street_address()

    @check_for_data
    def city(self):
        return self.service.city()

    @check_for_data
    def state(self):
        return self.service.state()

    @check_for_data
    def zip5(self):
        return self.service.zip5()

    @check_for_data
    def zip4(self):
        return self.service.zip4()

    class TexasAm():

        TEXAS_AM_BASE_URL = 'https://geoservices.tamu.edu/Services/Geocode/WebService/GeocoderWebServiceHttpNonParsed_V04_01.aspx'
        TEXAS_AM_REVERSE_BASE_URL = 'https://geoservices.tamu.edu/Services/ReverseGeocoding/WebService/v04_01/HTTP/default.aspx'

        def __init__(self, opts=None):
            try:
                self.apiKey = opts['apiKey']
                self.version = opts.get('version','4.01')
                self.format = opts.get('format', 'json')
                self.data = None
            except KeyError:
                print 'This service requires an apiKey and version.'
                raise KeyError

        def lookup(self, **params):

            params = {
                'apiKey': self.apiKey,
                'version': self.version,
                'streetAddress': params.get('street_address',''),
                'city': params.get('city',''),
                'state': params.get('state',''),
                'zip': params.get('zip5',''),
                'format': self.format
            }

            try:
                r = requests.get(self.TEXAS_AM_BASE_URL, params=params, verify=False)
                self.data = r.json() if self.format == 'json' else r.text
                # TODO convert other formats to correct json
            except:
                pass

        def reverse_lookup(self, lat, lng):

            params = {
                'apiKey': self.apiKey,
                'version': self.version,
                'lat': lat,
                'lon': lng,
                'format': self.format
            }

            try:
                r = requests.get(self.TEXAS_AM_REVERSE_BASE_URL, params=params, verify=False)
                self.data = r.json() if self.format == 'json' else r.text
                # TODO convert other formats to correct json
            except:
                pass

        def address(self):
            return {
                'street_address': self.street_address(),
                'city': self.city(),
                'state': self.state(),
                'zip5': self.zip5(),
                'zip4': self.zip4()
            }

        def street_address(self):
            return self.data['StreetAddresses'][0]['StreetAddress']

        def city(self):
            return self.data['StreetAddresses'][0]['City']

        def state(self):
            return self.data['StreetAddresses'][0]['State']

        def zip5(self):
            return self.data['StreetAddresses'][0]['Zip']

        def zip4(self):
            return self.data['StreetAddresses'][0]['ZipPlus4']

        def lat_long(self):
            return (self.data['OutputGeocodes'][0]['OutputGeocode']['Latitude'],
                    self.data['OutputGeocodes'][0]['OutputGeocode']['Longitude'])
