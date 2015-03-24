from wtforms import BooleanField, StringField, PasswordField, SelectField, TextAreaField, validators
from flask.ext.wtf import Form
import re
from lib import usps
from config import settings
from lib import geocoder
import sunlight

class RegistrationForm(Form):
    prefix = SelectField('Prefix',
                         choices=[(x,x) for x in ['Choose...','Mr.','Mrs.','Ms.','Dr.']],
                         validators=[validators.NoneOf(['Choose...'])])
    first_name = StringField('First name',
                             validators=[validators.DataRequired()])
    last_name = StringField('Last name',
                            validators=[validators.DataRequired()])
    street_address = StringField('Street address',
                                 validators=[validators.DataRequired()])
    street_address2 = StringField('Street address 2')
    city = StringField('City', [validators.DataRequired()])
    state = SelectField('State',
                        choices=[('Choose...','Choose...')]+[(state, state) for state in usps.CODE_TO_STATE.keys()],
                        validators=[validators.NoneOf(['Choose...'])])
    email = StringField('E-Mail', [validators.Email()])
    zip5 = StringField('Zipcode', [validators.Length(min=5, max=5)])
    zip4 = StringField('Zip 4', [validators.Length(min=4, max=4)])
    phone_number = StringField('Phone number',
                   [validators.Regexp(re.compile('^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'))])

    subject = StringField("Subject", [validators.Length(min=0, max=255)])
    msgbody = TextAreaField("Message", [validators.Length(min=1, max=8000)])

    accept_tos = BooleanField('I accept the terms of service and privacy policy', [validators.DataRequired()])

    def validate_district(self, legislators):
        sunlight.config.API_KEY = settings.SUNLIGHT_API_KEY

        data = sunlight.congress.locate_districts_by_zip(self.zip5.data)
        if data.count > 1: # need to try by geolocation
            geo = geocoder.Geocoder('TexasAm', {'apiKey':settings.TEXAS_AM_API_KEY})
            geo.lookup(street_address=self.street_address.data,
                       city=self.city.data,
                       state=self.state.data,
                       zip5=self.zip5.data)
            lat,lng = geo.lat_long()
            data = sunlight.congress.locate_districts_by_lat_lon(lat,lng)

        district = data[0]['district']

        does_not_represent = []
        for leg in legislators:
            if leg.state != self.state or (leg.chamber == 'house' and leg.district != district):
                does_not_represent.append(leg)

        return does_not_represent

    def save_to_models(self, msg):
        from models import db
        for field, val in self.data.iteritems():
            try:
                if hasattr(msg.user_message_info, field):
                    setattr(msg.user_message_info, field,val)
                if hasattr(msg, field):
                    setattr(msg, field, val)
            except:
                continue
        db.session.commit()