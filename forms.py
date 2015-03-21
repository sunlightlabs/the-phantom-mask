from wtforms import Form, BooleanField, StringField, PasswordField, SelectField, TextAreaField, validators
import re

STATE_ABBREV = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                'HI', 'ID', 'IL', 'IN', 'IO', 'KS', 'KY', 'LA', 'ME', 'MD',
                'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']

class RegistrationForm(Form):
    first_name = StringField('First name', [validators.DataRequired()])
    last_name = StringField('Last name', [validators.DataRequired()])
    street_address = StringField('Street address', [validators.DataRequired()])
    street_address2 = StringField('Street address 2')
    city = StringField('City', [validators.DataRequired()])
    state = SelectField('State', choices=[(state, state) for state in STATE_ABBREV])
    email = StringField('E-Mail', [validators.Email()])
    zip5 = StringField('Zipcode', [validators.Length(min=5, max=5)])
    zip4 = StringField('Zip 4', [validators.Length(min=4, max=4)])
    phone_number = StringField('Phone number',
                   [validators.Regexp(re.compile('^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'))])

    subject = StringField("Subject", [validators.Length(min=0, max=255)])
    msgbody = TextAreaField("Message", [validators.Length(min=1, max=8000)])

    accept_tos = BooleanField('I accept the terms of service and privacy policy', [validators.DataRequired()])