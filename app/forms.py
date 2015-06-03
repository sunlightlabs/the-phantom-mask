from wtforms import BooleanField, StringField, PasswordField, SelectField, TextAreaField, validators
from flask.ext.wtf import Form
import re
from lib import usps
from services import address_inferrence_service
from phantom_mask import db
from models import UserMessageInfo, AdminUser, User, db_first_or_create
import datetime
from flask.ext.wtf.recaptcha import RecaptchaField

class MyBaseForm(Form):

    def __init__(self, formdata, post_action_url, **kwargs):
        super(MyBaseForm, self).__init__(formdata, **kwargs)
        self.post_action_url = post_action_url

    def data_dict(self):
        """
        Gets data from form in dict with format {field.name: field.data ...}

        @return: dict of data
        @rtype: dict[str, (str|int|type)]
        """
        return {getattr(field, 'name'): getattr(field, 'data') for field in self}


class TokenResetForm(MyBaseForm):

    email = StringField('Email', validators=[validators.Email(message='Please enter a valid e-mail address.')])


class RecaptchaForm(MyBaseForm):

    recaptcha = RecaptchaField()


class LoginForm(MyBaseForm):

    username = StringField("Username", validators=[validators.DataRequired()])
    password = PasswordField("Password", validators=[validators.DataRequired()])

    def validate_credentials(self):
        if self.validate():
            admin = AdminUser.query.filter_by(username=self.username.data).first()
            if admin is not None and admin.check_password(self.password.data):
                return admin
        return False

class MessageForm(MyBaseForm):

    subject = StringField("Subject", [validators.Length(min=0, max=255)])
    msgbody = TextAreaField("Message", [validators.Length(min=1, max=8000)])

    @property
    def error_dict(self):
        return {field.label.text: field.errors for field in self}

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


class RegistrationForm(MyBaseForm):

    prefix = SelectField('Prefix',
                         choices=[(x,x) for x in ['', 'Mr.', 'Mrs.', 'Ms.']],
                         validators=[validators.DataRequired('Congressional offices require a title in order to accept any message.'),
                                     validators.NoneOf([''], message='Please select a prefix.')])
    first_name = StringField('First name',
                             validators=[validators.DataRequired(message="This field is required yo yo")])
    last_name = StringField('Last name',
                            validators=[validators.DataRequired()])
    street_address = StringField('Street address',
                                 validators=[validators.DataRequired()])
    street_address2 = StringField('Apt/Suite')
    city = StringField('City', [validators.DataRequired()])
    state = SelectField('State',
                        choices=[('', '')]+[(state, state) for state in usps.CODE_TO_STATE.keys()],
                        validators=[validators.NoneOf([''], message='Please select a state.')])
    email = StringField('E-Mail', [validators.Email()])
    zip5 = StringField('Zipcode', [validators.Regexp(re.compile('^\d{5}$'), message='Must be a 5 digit number.')])
    zip4 = StringField('Zip 4', [validators.Regexp(re.compile('^\d{4}$'), message='Must be a 4 digit number.')])
    phone_number = StringField('Phone number',
                   [validators.Regexp(re.compile('^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'),
                                      message="Please enter a valid phone number.")])

    accept_tos = BooleanField('I accept the terms of service and privacy policy', [validators.DataRequired()])

    @property
    def error_dict(self):
        return {field.label.text: field.errors for field in self}

    def initial_validate(self):
        self._errors = None
        success = True
        for field in ['prefix', 'first_name', 'last_name', 'street_address', 'zip5', 'phone_number']:
            if not getattr(self, field).validate(self):
                success = False
        return success

    def _autocomplete_email(self, email):
        self.email.data = email

    def _autocomplete_address(self):
        address = address_inferrence_service.address_lookup(
            street_address=self.street_address.data, city=self.city.data,
            state=self.state.data, zip5=self.zip5.data)

        self.city.data = address.get('city', '')
        self.street_address.data = address.get('street_address', '')
        self.zip5.data = address.get('zip5', '')
        self.zip4.data = address.get('zip4', '')
        self.state.data = address.get('state', '')

    def _autocomplete_tos(self):
        self.accept_tos.data = True

    def _autocomplete_zip(self):
        zipdata = self.zip5.data.split('-')
        try:
            self.zip5.data = zipdata[0]
        except:
            self.zip5.data = ''
        try:
            self.zip4.data = zipdata[1]
        except:
            self.zip4.data = ''

    def _autocomplete_phone(self):
        self.phone_number.data = re.sub("[^0-9]", "", self.phone_number.data)

    def resolve_zip4(self, force=False):
        if force or not self.zip4.data:
            self.zip4.data = address_inferrence_service.zip4_lookup(self.street_address.data,
                                                                    self.city.data,
                                                                    self.state.data,
                                                                    self.zip5.data
                                                                    )


    def validate_and_save_to_db(self, user, msg=None):
        """
        Validates the form and (if valid) saves the data to the database.

        @param user: the user
        @type user: models.User
        @param msg: the message
        @type msg: models.Message
        @return: True if validation and save is successful, False otherwise
        @rtype: boolean
        """
        self._autocomplete_tos()
        self._autocomplete_email(user.email)
        self._autocomplete_zip()
        self._autocomplete_phone()
        if self.validate():
            print "here323234"
            # get user's default info and either create new info or get the same info instance
            first_umi = UserMessageInfo.query.filter_by(user=user, default=True).first()
            print "wtff????"
            print user
            umi = first_umi if (first_umi and first_umi.accept_tos is None) \
                else UserMessageInfo.first_or_create(user.id, **self.data_dict())

            # check if the new user info differs from the newly submitted info and adjust appropriately
            if first_umi.id is not umi.id:
                first_umi.default = False
                umi.default = True
                if msg is not None:
                    msg.user_message_info = umi

            # save form data to models
            for field, val in self.data.iteritems():
                try:
                    setattr(umi, field, str(val))
                except:
                    return False

            # form is valid so user accepted tos at this time
            umi.accept_tos = datetime.datetime.now()

            # if everything succeeded then we commit and return True
            db.session.commit()
            return True
        else:
            return False