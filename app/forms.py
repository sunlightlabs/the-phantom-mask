from wtforms import BooleanField, StringField, PasswordField, SelectField, TextAreaField, validators
from flask.ext.wtf import Form
import re
from lib import usps
from services import address_inferrence_service, determine_district_service, geolocation_service
from phantom_mask import db
from models import UserMessageInfo, AdminUser
import datetime
from flask.ext.wtf.recaptcha import RecaptchaField
from wtforms.widgets import html_params, HTMLString
from cgi import escape
from models import Legislator, db_first_or_create, User, UserMessageInfo
from sqlalchemy import or_, and_, not_



class MyBaseForm(Form):

    def __init__(self, formdata, post_action_url='', **kwargs):
        super(MyBaseForm, self).__init__(formdata, **kwargs)
        self.post_action_url = post_action_url

    def set_post_action_url(self, url):
        self.post_action_url = url

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


class MyOption(object):

   def __call__(self, field, **kwargs):
       options = dict(kwargs, value=field._value())
       if field.checked:
           options['selected'] = True

       label = field.label.text
       render_params = (html_params(**options), escape(unicode(label)))

       return HTMLString(u'<option %s>%s</option>' % render_params)


class MySelectField(SelectField):

    def pre_validate(self, form):
        for v, _ in self.choices:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Please select a ' + self.label.text))


class BaseLookupForm(Form):

    street_address = StringField('Street address',
                                 validators=[validators.DataRequired(message="Street address is required."),
                                             validators.Length(min=1, max=256)])
    street_address2 = StringField('Apt/Suite')
    city = StringField('City', [validators.DataRequired(message="City is required."),
                                validators.Length(min=1, max=256)])
    state = MySelectField('State',
                        choices=[('State', 'State')]+[(state, state) for state in usps.CODE_TO_STATE.keys()],
                        validators=[validators.NoneOf(['State'], message='Please select a state.')],
                        option_widget=MyOption())
    zip5 = StringField('Zipcode', [validators.Regexp(re.compile('^\d{5}$'), message='Zipcode and Zip+4 must have form XXXXX-XXXX. Lookup up <a target="_blank" href="https://tools.usps.com/go/ZipLookupAction!input.action">here</a>')])
    zip4 = StringField('Zip 4', [validators.Regexp(re.compile('^\d{4}$'), message='Zipcode and Zip+4 must have form XXXXX-XXXX. Lookup up <a target="_blank" href="https://tools.usps.com/go/ZipLookupAction!input.action">here</a>')])


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

    def validate(self):
        self._autocomplete_zip()
        validation = super(BaseLookupForm, self).validate()
        if not validation:
            self.zip5.data = self.zip5.data + '-' + self.zip4.data
        return validation


class LegislatorLookupForm(MyBaseForm, BaseLookupForm):

    def _autocomplete_zip(self):
        super(LegislatorLookupForm, self)._autocomplete_zip()

    def lookup_legislator(self):
        data = determine_district_service.determine_district(zip5=self.zip5.data)
        if data is None:
            latitude, longitude = geolocation_service.geolocate(street_address=self.street_address,
                                                                city=self.city,
                                                                state=self.state,
                                                                zip5=self.zip5)
            data = determine_district_service.determine_district(latitude=latitude, longitude=longitude)

        return Legislator.query.filter(
            and_(Legislator.contactable.is_(True), Legislator.state == data.get('state'),
            or_(Legislator.district.is_(None), Legislator.district == data.get('district')))).all()


class RegistrationForm(MyBaseForm, BaseLookupForm):

    prefix = MySelectField('Prefix',
                         choices=[(x,x) for x in ['Title', 'Mr.', 'Mrs.', 'Ms.']],
                         validators=[validators.DataRequired(message='A title prefix is required.'),
                                     validators.NoneOf(['Title'], message='Please select a prefix.')],
                         option_widget=MyOption())
    first_name = StringField('First name',
                             validators=[validators.DataRequired(message="First name is required."),
                                         validators.Length(min=1, max=50)])
    last_name = StringField('Last name',
                            validators=[validators.DataRequired(message="Last name is required."),
                                        validators.Length(min=1, max=50)])

    email = StringField('E-Mail', [validators.Email()])
    phone_number = StringField('Phone number',
                   [validators.Regexp(re.compile('^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'),
                                      message="Please enter a valid phone number.")])

    # accept_tos = BooleanField('I accept the terms of service and privacy policy', [validators.DataRequired()])

    @property
    def ordered_fields(self):
        return [
            self.prefix,
            self.first_name,
            self.last_name,
            self.street_address,
            self.street_address2,
            self.city,
            self.state,
            self.email,
            self.zip5,
            self.zip4,
            self.phone_number
        ]

    @property
    def ordered_fields_errors(self):
        errors = self.ordered_fields
        if self.zip5.errors and self.zip4.errors:
            errors.remove(self.zip4)
        return errors

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

    #def _autocomplete_tos(self):
    #    self.accept_tos.data = True

    def _autocomplete_zip(self):
        super(RegistrationForm, self)._autocomplete_zip()

    def _autocomplete_phone(self):
        self.phone_number.data = re.sub("[^0-9]", "", self.phone_number.data)

    def _doctor_names(self):
        self.first_name.data = self.first_name.data.replace(' ', '')
        self.last_name.data = self.last_name.data.replace(' ', '')

    def resolve_zip4(self, force=False):
        if force or not self.zip4.data:
            self.zip4.data = address_inferrence_service.zip4_lookup(self.street_address.data,
                                                                    self.city.data,
                                                                    self.state.data,
                                                                    self.zip5.data
                                                                    )

    def signup(self):
        """

        @return:
        @rtype:
        """
        # create or get the user and his default information
        user = db_first_or_create(User, email=self.email.data)
        umi = db_first_or_create(UserMessageInfo, user_id=user.id, default=True)
        status, result = self.validate_and_save_to_db(user, accept_tos=False)
        return (user, result) if status else (status, result)

    def update_address(self):
        pass



    def validate_and_save_to_db(self, user, msg=None, accept_tos=True):
        """
        Validates the form and (if valid) saves the data to the database.

        @param user: the user
        @type user: models.User
        @param msg: the message
        @type msg: models.Message
        @return: True if validation and save is successful, False otherwise
        @rtype: boolean
        """
        # self._autocomplete_tos()

        self._autocomplete_email(user.email)
        self._autocomplete_phone()
        self._doctor_names()

        if self.validate():
            # get user's default info and either create new info or get the same info instance
            first_umi = UserMessageInfo.query.filter_by(user=user, default=True).first()
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
                    return False, 'error'

            # form is valid so user accepted tos at this time
            umi.accept_tos = datetime.datetime.now() if accept_tos else None

            # if everything succeeded then we commit and return True
            db.session.commit()

            if umi.determine_district(force=True) is None:
                return False, 'district_error'

            return True, 'success'
        else:
            return False, 'invalid_form_error'