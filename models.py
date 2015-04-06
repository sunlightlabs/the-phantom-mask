from phantom_mask import db
from config import settings
import datetime
import uuid
from contextlib import contextmanager
from lib import phantom_on_the_capitol
import urllib
import json
from lib import usps
import random
from dateutil import parser
import pytz
from services import determine_district_service
from services import geolocation_service
from lib.dict_ext import remove_keys
from lib.dict_ext import sanitize_keys
from sqlalchemy.sql import or_

@contextmanager
def get_db_session():
    try:
        yield db.session
    finally:
        db.session.remove()


def set_attributes(model, attrs):
    for k, v in attrs:
        try:
            setattr(model, k, v)
        except:
            continue
    return model

def db_add_and_commit(toadd):
    try:
        db.session.add(toadd)
        db.session.commit()
        return toadd
    except:
        db.session.rollback()
        return None


def db_first_or_create(cls, **kwargs):
    model = cls.query.filter_by(**kwargs).first()
    if model is None:
        model = cls(**kwargs)
        db_add_and_commit(model)
    return model


def to_json(inst, cls):
    """
    Jsonify the sql alchemy query result.
    """
    convert = dict()
    # add your coversions for things like datetime's
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)
        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif v is None:
            d[c.name] = str()
        else:
            d[c.name] = v
    return json.dumps(d)


class Legislator(db.Model):
    """
    Thin model for storing data on current representatives.
    """
    bioguide_id = db.Column(db.String(7), primary_key=True)
    chamber = db.Column(db.String(20))
    state = db.Column(db.String(2))
    district = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(3))
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    oc_email = db.Column(db.String(256))
    contactable = db.Column(db.Boolean, default=True)

    messages = db.relationship('MessageLegislator', backref='legislator', lazy='dynamic')

    @property
    def json(self):
        return to_json(self, self.__class__)

    def full_title(self):
        return {
            'Com': 'Commissioner',
            'Del': 'Delegate',
            'Rep': 'Representative',
            'Sen': 'Senator'
        }.get(self.title, 'Representative')

    def full_name(self):
        return self.first_name + " " + self.last_name

    def title_and_last_name(self):
        return self.title + " " + self.last_name

    def title_and_full_name(self):
        return self.title + " " + self.full_name()

    def image_url(self, size='small'):
        dimensions = {
            'small': '225x275',
            'large': '450x550'
        }

        dim = dimensions.get(size, dimensions.values()[0])
        return "https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/" + dim + "/" + self.bioguide_id + '.jpg'

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True)
    user_infos = db.relationship('UserMessageInfo', backref='user')

    @classmethod
    def global_captcha(cls):
        return Message.query.filter((datetime.datetime.now() - datetime.timedelta(hours=settings.USER_MESSAGE_LIMIT_HOURS)
                                    < Message.sent_at)).count() > settings.GLOBAL_HOURLY_CAPTCHA_THRESHOLD

    def rate_limit_status(self):
        """
        Determines if a user should be rate limited (or blocked if argument provided

        @return status of rate limit [block, captcha, free]
        @rtype string
        """
        if self.global_captcha():
            return 'captcha'

        count = self.messages().filter(
            (datetime.datetime.now() - datetime.timedelta(hours=settings.USER_MESSAGE_LIMIT_HOURS)
                < Message.sent_at)).count()
        if count > settings.USER_MESSAGE_LIMIT_BLOCK_COUNT:
            return 'block'
        elif count > settings.USER_MESSAGE_LIMIT_CAPTCHA_COUNT:
            return 'captcha'
        else:
            return 'free'

    def messages(self, **filters):
        return Message.query.filter_by(**filters).join(UserMessageInfo).join(User).filter_by(email=self.email)

    @property
    def default_info(self):
        return UserMessageInfo.query.filter_by(user_id=self.id, default=True).first()

    @property
    def json(self):
        return to_json(self, self.__class__)

class UserMessageInfo(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    default = db.Column(db.Boolean, default=False)
    accept_tos = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    prefix = db.Column(db.String(32), info={'user_input': True})
    first_name = db.Column(db.String(256), info={'user_input': True})
    last_name = db.Column(db.String(256), info={'user_input': True})
    street_address = db.Column(db.String(1000), info={'user_input': True})
    street_address2 = db.Column(db.String(1000), info={'user_input': True})
    city = db.Column(db.String(256), info={'user_input': True})
    state = db.Column(db.String(2), info={'user_input': True})
    zip5 = db.Column(db.String(5), info={'user_input': True})
    zip4 = db.Column(db.String(4), info={'user_input': True})
    phone_number = db.Column(db.String(20), info={'user_input': True})

    latitude = db.Column(db.String(256))
    longitude = db.Column(db.String(256))

    district = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    messages = db.relationship('Message', backref='user_message_info')

    @classmethod
    def first_or_create(cls, user_id, created_at=datetime.datetime.now, **kwargs):
        user = User.query.filter_by(id=user_id).first()
        if user is not None:
            sanitize_keys(kwargs, cls.user_input_columns())
            umi = UserMessageInfo.query.filter_by(**kwargs).first()
            if umi is not None:
                return umi
            else:
                created_at = parser.parse(created_at) if type(created_at) is str else created_at().replace(tzinfo=pytz.timezone('US/Eastern'))
                umi = UserMessageInfo(user_id=user.id, created_at=created_at, **kwargs)
                db_add_and_commit(umi)
                return umi

    @classmethod
    def user_input_columns(cls):
        ui_cols = []
        for col in cls.__table__.columns:
            if 'user_input' in col.info and col.info['user_input']:
                ui_cols.append(col.name)
        return ui_cols

    def check_for_validate_tos(self):
        if self.accept_tos is None or (datetime.datetime.now() - self.accept_tos).days >= settings.TOS_DAYS_VALID:
            self.accept_tos = None
            db.session.commit()
            return False
        return True

    def mailing_address(self):
        return self.street_address + ', ' + self.street_address2 + ', '\
               + self.city + ', ' + self.state + ' ' + self.zip5 + '-' + self.zip4

    def geolocate_address(self):
        """
        Retrieves the latitude and longitude of the address information

        """
        if self.latitude is None and self.longitude is None:
            self.latitude, self.longitude = geolocation_service.geolocate(self.street_address,
                                                                          self.city,
                                                                          self.state,
                                                                          self.zip5)
            db.session.commit()
            return self.latitude, self.longitude

    def determine_district(self):
        district = determine_district_service.determine_district(zip5=self.zip5)
        if district is None:
            self.geolocate_address()
            district = determine_district_service.determine_district(latitude=self.latitude, longitude=self.longitude)

        try:
            self.district = int(district)
            db.session.commit()
            return self.district
        except:
            print "Unable to determine district for " + self.mailing_address()

    @property
    def members_of_congress(self):
        if self.district is None:
            self.determine_district()
        return Legislator.query.filter_by(district=UserMessageInfo.district.in_({None, self.district}),
                                          state=self.state).all()

    @property
    def json(self):
        return to_json(self, self.__class__)


class Message(db.Model):
    """
    Stores message information from email
    """

    @staticmethod
    def uid_creator():
        """
            Checks for collisions and returns a uid for a Message object.

            @return: [String] 32 character uid /^[a-z0-9]{32}$/
        """
        while True:
            potential_token = uuid.uuid4().hex
            if Message.query.filter_by(verification_token=potential_token).count() == 0:
                return potential_token

    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.datetime.now)
    subject = db.Column(db.String(256))
    msgbody = db.Column(db.String(8000))

    # belongs to
    user_message_info_id = db.Column(db.Integer, db.ForeignKey('user_message_info.id'))

    # has many
    to_legislators = db.relationship('MessageLegislator', backref='message')

    # email uid from postmark
    email_uid = db.Column(db.String(1000))
    # for follow up email to enter in address information
    verification_token = db.Column(db.String(32), default=uid_creator.__func__)

    @property
    def email(self): return self.user_message_info.user.email
    @property
    def prefix(self): return self.user_message_info.prefix
    @property
    def first_name(self): return self.user_message_info.first_name
    @property
    def last_name(self): return self.user_message_info.last_name
    @property
    def street_address(self): return self.user_message_info.street_address
    @property
    def street_address2(self): return self.user_message_info.street_address2
    @property
    def city(self): return self.user_message_info.city
    @property
    def state(self): return self.user_message_info.state
    @property
    def zip5(self): return self.user_message_info.zip5
    @property
    def zip4(self): return self.user_message_info.zip4
    @property
    def phone_number(self): return self.user_message_info.phone_number

    def verification_link(self):
        """
        Generates the full verification link to this message.

        @return: [String] full url to verification link
        """
        return settings.BASE_URL + '/verify/' + self.verification_token + '?' + urllib.urlencode({'email':self.user_message_info.user.email})

    def get_legislators(self, as_dict=False):
        """
        Retrieves the legislator models to which this message is to be sent.

        @param as_dict: [Boolean] if True, the method will return a dictionary with bioguide_ids as keys. False = list.
        @return: [List<Legislator>|Dictionary]
        """
        if as_dict:
            toReturn = {}
            for leg in self.to_legislators:
                l = Legislator.query.filter_by(bioguide_id=leg.legislator_id).first()
                toReturn[l.bioguide_id] = l
            return toReturn
        else:
            return [Legislator.query.filter_by(bioguide_id=leg.legislator_id).first() for leg in self.to_legislators]

    def namespaced_to_legislators(self):
        toReturn = {}
        for msg_leg in self.to_legislators: toReturn[msg_leg.legislator.bioguide_id] = msg_leg
        return toReturn

    def send(self):
        """
        Attempts to the send this message using phantom on the capitol.

        @return:
        """

        for msg_leg in self.to_legislators:
            msg_leg.send()

        """
        send_to = dict(zip([x.legislator.bioguide_id for x in self.to_legislators], [ml for ml in self.to_legislators]))

        for bioguide_id, ra in phantom_on_the_capitol.retrieve_form_elements(send_to.keys()).iteritems():
            json_dict = send_to[bioguide_id].map_to_contact_congress()
            for step in ra['required_actions']:
                field = step.get('value')
                options = step.get('options_hash')
                if type(options) is dict: options = options.keys()
                if options is not None:
                    if field not in json_dict['fields'] or json_dict['fields'][field] not in options:
                        json_dict['fields'][field] = random.choice(options)
                if field not in json_dict['fields'].keys():
                    print 'What the heck is ' + step.get('value') + ' in ' + bioguide_id + '?'
            status = phantom_on_the_capitol.fill_out_form(json_dict)
            send_to[bioguide_id].send_status = json.dumps(status)
        db.session.commit()
        return send_to
        """

    def map_to_contact_congress_fields(self):
        umi = self.user_message_info
        return {
            '$NAME_PREFIX': umi.prefix,
            '$NAME_FIRST': umi.first_name,
            '$NAME_LAST': umi.last_name,
            '$NAME_FULL': umi.first_name + ' ' + umi.last_name,
            '$ADDRESS_STREET': umi.street_address,
            '$ADDRESS_STREET_2': umi.street_address2,
            '$ADDRESS_CITY': umi.city,
            '$ADDRESS_ZIP5': umi.zip5,
            '$ADDRESS_ZIP4': umi.zip4,
            "$ADDRESS_ZIP_PLUS_4": umi.zip5 + '-' + umi.zip4,
            '$EMAIL': umi.user.email,
            '$SUBJECT': self.subject,
            '$MESSAGE': self.msgbody,
            '$ADDRESS_STATE_POSTAL_ABBREV': umi.state,
            '$PHONE': umi.phone_number,
            '$ADDRESS_STATE_FULL': usps.CODE_TO_STATE.get(umi.state)
        }

    #def __repr__(self):
    #    return '<User %r>' % (self.name)

class MessageLegislator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.Integer, db.ForeignKey('legislator.bioguide_id'))
    send_status = db.Column(db.String(4096), default='{"status": "unsent"}') # stringified JSON

    def get_send_status(self):
        """
        Retrieves the current status of the message to the legislator.

        @return: [Dictionary] dictionary detailing the status of the message
        """
        try:
            return json.loads(self.send_status)
        except:
            return self.send_status

    def send(self):
        for bioguide_id, ra in phantom_on_the_capitol.retrieve_form_elements([self.legislator.bioguide_id]).iteritems():
            json_dict = self.map_to_contact_congress()
            for step in ra['required_actions']:
                field = step.get('value')
                options = step.get('options_hash')
                if type(options) is dict:
                    options = options.keys()
                if options is not None:
                    if field not in json_dict['fields'] or json_dict['fields'][field] not in options:
                        json_dict['fields'][field] = random.choice(options) # TODO need smarter topic selection
                if field not in json_dict['fields'].keys():
                    print 'What the heck is ' + step.get('value') + ' in ' + bioguide_id + '?'
            status = phantom_on_the_capitol.fill_out_form(json_dict)
            self.send_status = json.dumps(status)
        db.session.commit()

    def map_to_contact_congress(self, campaign_tag=False):
        data = {
            'bio_id': self.legislator.bioguide_id,
            'fields': self.message.map_to_contact_congress_fields()
        }
        if campaign_tag:
            data['campaign_tag'] = self.message.email_uid

        return data

    @property
    def json(self):
        return to_json(self, self.__class__)