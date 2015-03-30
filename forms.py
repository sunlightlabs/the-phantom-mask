from wtforms import BooleanField, StringField, PasswordField, SelectField, TextAreaField, validators
from flask.ext.wtf import Form
import re
from lib import usps
from lib.dict_ext import remove_keys
from services import zip_inferrence_service
from services.determine_district_service import determine_district

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

    def resolve_zip4(self):
        self.zip4.data = zip_inferrence_service.zip4_lookup(self.street_address.data,
                                                            self.city.data,
                                                            self.state.data,
                                                            self.zip5.data
                                                            )

    def validate_district(self, legislators):
        district = determine_district(zip5=self.zip5.data,
                                      street_address=self.street_address.data,
                                      city=self.city.data,
                                      state=self.state.data)

        does_not_represent = []
        for leg in legislators:
            if leg.state != self.state or (leg.chamber == 'house' and leg.district != district):
                does_not_represent.append(leg)

        return does_not_represent

    def populate_data_from_message(self, msg):
        """
        Sets form data equal to the default message data

        @param msg: [Message] message model instance
        @return:
        """
        for field in self:
            try:
                setattr(field, 'data', getattr(msg, field.name))
            except:
                continue

    def save_to_models(self, msg):
        """
        Saves data from form to relevant models.

        @param msg: [Message] the message model instance
        @return:
        """
        from models import db
        from models import UserMessageInfo

        # check if user has input new contact information
        kwargs = {getattr(field, 'name'): getattr(field, 'data') for field in self}
        umi = UserMessageInfo.first_or_create(msg.user_message_info.user.id, **kwargs)
        if msg.user_message_info.id != umi.id:
            msg.user_message_info.default = False
            umi.default = True
            msg.user_message_info = umi
            db.session.commit()

        # save form data to models
        for field, val in self.data.iteritems():
            try:
                setattr(msg, field, val)
            except:
                continue
        db.session.commit()