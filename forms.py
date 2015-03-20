from wtforms import Form, BooleanField, StringField, PasswordField, SelectField, validators
import re

class RegistrationForm(Form):
    firstname = StringField('First name', [validators.DataRequired()])
    lastname = StringField('Last name', [validators.DataRequired()])
    street_address = StringField('Street address', [validators.DataRequired()])
    street_address2 = StringField('Street address 2')
    city = StringField('City', [validators.DataRequired()])
    state = SelectField('State', choices=[12,213,123])
    zipcode = StringField('Zipcode', [validators.Length(min=5, max=5)])
    phone_number = StringField('Phone number',
                   [validators.Regexp(re.compile('^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'))])

    accept_tos = BooleanField('I accept the terms of service and privacy policy', [validators.DataRequired()])