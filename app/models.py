from phantom_mask import db
from config import settings
import datetime
import uuid
from contextlib import contextmanager
import urllib
import json
from lib import usps, phantom_on_the_capitol, select_solver
import random
from dateutil import parser
import pytz
from lib.int_ext import ordinal
from services import determine_district_service
from services import address_inferrence_service
from services import geolocation_service
from lib.dict_ext import remove_keys
from lib.dict_ext import sanitize_keys
from sqlalchemy import or_, and_, not_
from flask import url_for
import jellyfish
import sys
from util import render_without_request
from helpers import abs_base_url
from flask.ext.login import UserMixin
import flask_login
from flask_admin.contrib.sqla import ModelView
from flask import jsonify, redirect, request

import os

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


def db_add_and_commit(model, commit=True):
    try:
        db.session.add(model)
        if commit:
            db.session.commit()
        return model
    except:
        db.session.rollback()
        return None


def db_first_or_create(cls, commit=True, **kwargs):
    model = cls.query.filter_by(**kwargs).first()
    if model is None:
        model = cls(**kwargs)
        db_add_and_commit(model, commit)
    return model


def to_json(inst, cls):
    """
    Jsonify the sql alchemy query result.

    @param inst: instance to jsonify
    @type inst:
    @param cls: class of the instance to jsonify
    @type cls:
    @return: json string representing the isntance
    @rtype: string
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


def uid_creator(cls, *args):
    """
    Creates a potential 64 character string uid, checks for collisions in input class,
    and returns a uid.


    @param cls: string of class name inherited from db.Model
    @type cls: string
    @param args: one position argument for name of the uid attribute on the class
    @type args: string
    @return: function that will generate the uid
    @rtype: function
    """
    def create_uid():
        while True:
            potential_token = uuid.uuid4().hex + uuid.uuid4().hex
            if getattr(sys.modules[__name__], cls).query.filter_by(**{args[0]: potential_token}).count() == 0:
                return potential_token
    return create_uid

class MyModelView(ModelView):

    def _handle_view(self, name, **kwargs):
        if name != 'login' and not self.is_accessible():
            return redirect(url_for('admin.login', next=request.url))

    def is_accessible(self):
        return flask_login.current_user.is_authenticated()


class BaseAnalytics(object):

    def __init__(self, model):
        self.model = model
        self.today = datetime.datetime.today()
        self.today_start = self.today.replace(hour=0, minute=0, second=0, microsecond=0)

    def total_count(self):
        return self.model.query.count()

    def new_today(self):
        return self.new_last_n_days(0)

    def new_last_n_days(self, n_days):
        return self.model.query.filter(self.model.created_at > (self.today_start - datetime.timedelta(days=n_days))).count()

    def new_in_range(self, start_days, end_days):
        return self.model.query.filter(and_(self.model.created_at > (self.today_start - datetime.timedelta(days=start_days)),
                               self.model.created_at < (self.today_start - datetime.timedelta(days=end_days)))).count()

    def growth_rate(self, n_days):
        last_n = float(self.new_last_n_days(n_days))
        prev_last_n = float(self.new_in_range(n_days*2, n_days))
        return (last_n - prev_last_n) / last_n





class Legislator(db.Model):
    """
    Thin model for storing data on current representatives.
    """

    class ModelView(MyModelView):

        column_searchable_list = ['bioguide_id', 'chamber', 'state', 'title',
                                  'first_name', 'last_name', 'oc_email', 'contact_form']

    bioguide_id = db.Column(db.String(7), primary_key=True, info={'official': True})
    chamber = db.Column(db.String(20),info={'official': True})
    state = db.Column(db.String(2),info={'official': True})
    district = db.Column(db.Integer, nullable=True, info={'official': True})
    title = db.Column(db.String(3), info={'official': True})
    first_name = db.Column(db.String(256), info={'official': True})
    last_name = db.Column(db.String(256), info={'official': True})
    contact_form = db.Column(db.String(1024), info={'official': True})
    oc_email = db.Column(db.String(256), info={'official': True})
    contactable = db.Column(db.Boolean, default=True)

    messages = db.relationship('MessageLegislator', backref='legislator', lazy='dynamic')

    @classmethod
    def congress_api_columns(cls):
        return [col.name for col in cls.__table__.columns if 'official' in col.info and col.info['official']]


    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

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

    def full_title_and_full_name(self):
        return self.full_title() + " " + self.full_name()

    def image_url(self, size='small'):
        dimensions = {
            'small': '225x275',
            'large': '450x550'
        }
        return "https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/" + \
               dimensions.get(size, dimensions.values()[0]) + "/" + self.bioguide_id + '.jpg'

from werkzeug.security import generate_password_hash, check_password_hash

class AdminUser(db.Model, UserMixin):

    class ModelView(MyModelView):
        column_searchable_list = ['username']

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    pw_hash = db.Column(db.String(66), unique=False, nullable=False)

    # UserMixin for flask.ext.login
    active = db.Column(db.Boolean, default=True)
    anonymous = db.Column(db.Boolean, default=False)

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return self.anonymous

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def get_id(self):
        return unicode(self.id)



class User(db.Model):

    class ModelView(MyModelView):
        column_searchable_list = ['email', 'address_change_token']

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    user_infos = db.relationship('UserMessageInfo', backref='user')
    role = db.Column(db.Integer, default=0)
    address_change_token = db.Column(db.String(64), default=uid_creator('User', 'address_change_token'))

    ROLES = {
        0: 'user',
        1: 'special',
        2: 'admin'
    }

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    def __html__(self):
        return render_without_request('snippets/user.html', user=self)

    @classmethod
    def global_captcha(cls):
        return Message.query.filter((datetime.datetime.now() - datetime.timedelta(hours=settings.USER_MESSAGE_LIMIT_HOURS)
                                    < Message.sent_at)).count() > settings.GLOBAL_HOURLY_CAPTCHA_THRESHOLD


    def new_address_change_token(self):
        self.address_change_token = uid_creator('User', 'address_change_token')()
        db.session.commit()
        return self.address_change_token

    def get_role(self):
        return self.ROLES.get(self.role, 'unknown')

    def is_admin(self):
        return self.ROLES.get(self.role) is 'admin'

    def is_special(self):
        return self.ROLES.get(self.role) is 'special'

    def can_skip_rate_limit(self):
        return self.is_admin() or self.is_special()

    def rate_limit_status(self):
        """
        Determines if a user should be rate limited (or blocked if argument provided

        @return status of rate limit [block, captcha, free]
        @rtype string
        """

        if self.can_skip_rate_limit():
            return 'free'

        if User.global_captcha():
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

    def last_message(self):
        return self.messages()[-1]

    def address_change_link(self, path=None):
        """
        Gets the url for this user to change their address.

        @param path: validation url from view
        @type path: string
        @return: URL for confirmation email
        @rtype: string
        """
        return settings.BASE_URL + (path if path is not None else '/validate/' + self.address_change_token) + \
            '?' + urllib.urlencode({'email': self.email})

    @property
    def default_info(self):
        return UserMessageInfo.query.filter_by(user_id=self.id, default=True).first()

    @property
    def json(self):
        return to_json(self, self.__class__)

    class Analytics(BaseAnalytics):

        def __init__(self):
            super(User.Analytics, self).__init__(User)

        def users_with_verified_districts(self):
            return UserMessageInfo.query.join(User).filter(
                and_(UserMessageInfo.default.is_(True), not_(UserMessageInfo.district.is_(None)))).count()

class UserMessageInfo(db.Model):

    class ModelView(MyModelView):
        column_searchable_list = ['first_name', 'last_name', 'street_address', 'street_address2', 'city', 'state',
                                  'zip5', 'zip4', 'phone_number']

    # meta data
    id = db.Column(db.Integer, primary_key=True)
    default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    # input by user
    prefix = db.Column(db.String(32), default='', info={'user_input': True})
    first_name = db.Column(db.String(256), default='', info={'user_input': True})
    last_name = db.Column(db.String(256), default='', info={'user_input': True})
    street_address = db.Column(db.String(1000), default='', info={'user_input': True})
    street_address2 = db.Column(db.String(1000), default='', info={'user_input': True})
    city = db.Column(db.String(256), default='', info={'user_input': True})
    state = db.Column(db.String(2), default='', info={'user_input': True})
    zip5 = db.Column(db.String(5), default='', info={'user_input': True})
    zip4 = db.Column(db.String(4), default='', info={'user_input': True})
    phone_number = db.Column(db.String(20), default='', info={'user_input': True})
    accept_tos = db.Column(db.DateTime, default=None)

    # set by methods based on input address information above
    latitude = db.Column(db.String(256))
    longitude = db.Column(db.String(256))
    district = db.Column(db.Integer, default=None)

    # relations
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    messages = db.relationship('Message', backref='user_message_info')

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    @classmethod
    def first_or_create(cls, user_id, created_at=datetime.datetime.now, **kwargs):
        user = User.query.filter_by(id=user_id).first()
        if user is not None:
            sanitize_keys(kwargs, cls.user_input_columns())
            umi = UserMessageInfo.query.filter_by(**kwargs).first()
            if umi is not None: return umi
            else:
                created_at = parser.parse(created_at) if type(created_at) is str else created_at().replace(tzinfo=pytz.timezone('US/Eastern'))
                umi = UserMessageInfo(user_id=user.id, created_at=created_at, **kwargs)
                db_add_and_commit(umi)
                return umi

    @classmethod
    def user_input_columns(cls):
        return [col.name for col in cls.__table__.columns if 'user_input' in col.info and col.info['user_input']]

    def humanized_district(self):
        return (ordinal(self.district) if self.district > 0 else 'At-Large') + \
            ' Congressional district of ' + usps.CODE_TO_STATE.get(self.state)

    def should_update_address_info(self):
        """
        Determines if user needs to update their address information.

        @return: True if they need to update, False otherwise
        @rtype: boolean
        """
        return self.accept_tos is None or (datetime.datetime.now() - self.accept_tos).days >= settings.ADDRESS_DAYS_VALID

    def mailing_address(self):
        return self.street_address + ' ' + self.street_address2 + ', '\
               + self.city + ', ' + self.state + ' ' + self.zip5 + '-' + self.zip4

    def complete_information(self):
        if self.district is None:
            self.determine_district(force=True)
        if not self.zip4:
            self.zip4_lookup(force=True)

    def zip4_lookup(self, force=False):
        if force or not self.zip4:
            try:
                self.zip4 = address_inferrence_service.zip4_lookup(self.street_address,
                                                                   self.city,
                                                                   self.state,
                                                                   self.zip5
                                                                   )
                db.session.commit()
            except:
                db.session.rollback()

    def geolocate_address(self, force=False):
        """
        Retrieves the latitude and longitude of the address information.

        @return: latitude, longitude tuple
        @rtype: (string, string)
        """
        if force or (self.latitude is None and self.longitude is None):
            try:
                self.latitude, self.longitude = geolocation_service.geolocate(self.street_address,
                                                                              self.city,
                                                                              self.state,
                                                                              self.zip5)
                db.session.commit()
                return self.latitude, self.longitude
            except:
                return None, None

    def determine_district(self, force=False):
        """
        Determines the district of information associated with this address.

        @param force: whether to force an update of district
        @type force: boolean
        @return: district of address information
        @rtype: int
        """
        if not force and self.district is not None:
            return self.district

        district = determine_district_service.determine_district(zip5=self.zip5)
        if district is None:
            self.geolocate_address()
            district = determine_district_service.determine_district(latitude=self.latitude, longitude=self.longitude)

        try:
            self.district = district
            db.session.commit()
            return self.district
        except:
            print "Unable to determine district for " + self.mailing_address()
            return None


    @property
    def members_of_congress(self):
        if self.district is None:
            self.determine_district()
        return Legislator.query.filter(
            and_(Legislator.contactable.is_(True), Legislator.state == self.state,
                 or_(Legislator.district.is_(None), Legislator.district == self.district))).all()

    @property
    def json(self):
        return to_json(self, self.__class__)


class Topic(db.Model):

    class ModelView(MyModelView):
        column_searchable_list = ['name']

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), unique=True)
    wikipedia_parent = db.Column(db.Integer, db.ForeignKey('topic.id'))
    msg_legs = db.relationship('MessageLegislator', backref='topic')

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    @staticmethod
    def topic_for_message(choices, message):
        return select_solver.choose(message.msgbody, [t.name.lower() for t in Topic.topics_from_choices(choices)])

    @staticmethod
    def topics_from_choices(choices):
        return list(set([top if top.wikipedia_parent is None else Topic.query.filter_by(id=top.wikipedia_parent).first()
                        for top in Topic.query.filter(or_(*[(Topic.name == c.lower()) for c in choices])).all()]))

    @classmethod
    def populate_topics_from_phantom_forms(cls):
        all_forms = phantom_on_the_capitol.retrieve_form_elements([x.bioguide_id for x in Legislator.query.all()])
        all_topics = {}
        for legislator, req in all_forms.iteritems():
            for key, val in req.iteritems():
                for step in val:
                    if step['value'] == '$TOPIC':
                        if type(step['options_hash']) is dict:
                            keys = step['options_hash'].keys()
                        else:
                            keys = step['options_hash']
                        for k in keys:
                            k = k.strip()
                            if all_topics.has_key(k):
                                all_topics[k] += 1
                            else:
                                all_topics[k] = 1

        failed_topics = []
        for topic, count in all_topics.iteritems():
            result = select_solver.choose('test', [topic.lower()])
            if result is None:
                failed_topics.append(topic.lower())
            elif result:
                db_first_or_create(Topic, name=topic.lower())

        all_topics = Topic.query.filter_by(wikipedia_parent=None)

        for f_topic in failed_topics:
            try:
                lowest = (None, None)
                for topic in all_topics:
                    print topic.name, f_topic
                    d = jellyfish.damerau_levenshtein_distance(unicode(str(topic.name)), unicode(str(f_topic)))
                    if lowest[0] is None or lowest[1] > d:
                        lowest = (topic, d)
                print 'Adding ' + f_topic + ' with parent ' + lowest[0].name
                db_first_or_create(Topic, name=f_topic, wikipedia_parent=lowest[0].id)
            except:
                continue

    @property
    def json(self):
        return to_json(self, self.__class__)

class Message(db.Model):

    class ModelView(MyModelView):
        column_searchable_list = ['to_originally', 'subject', 'msgbody', 'verification_token']

        def scaffold_form(self):
            from wtforms import SelectMultipleField
            form_class = super(Message.ModelView, self).scaffold_form()
            form_class.legislators = SelectMultipleField('Add Legislators', choices=[(x.bioguide_id,x.bioguide_id) for x in Legislator.query.all()])
            return form_class

        def update_model(self, form, model):
            if super(Message.ModelView, self).update_model(form, model):
                if model.set_legislators(Legislator.query.filter(Legislator.bioguide_id.in_(form.legislators.data)).all()):
                    return True

        def validate_form(self, form):
            if super(Message.ModelView, self).validate_form(form):
                legs = Legislator.query.filter(Legislator.bioguide_id.in_(form.legislators.data))
                if len(form.legislators.data) != legs.count():
                    form.legislators.errors = ['Legislators with provided bioguides do not exist.']
                    return False
                return True

    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.datetime.now)
    # original recipients from email as json list
    to_originally = db.Column(db.String(8000))
    subject = db.Column(db.String(500))
    msgbody = db.Column(db.String(8000))

    # relations
    user_message_info_id = db.Column(db.Integer, db.ForeignKey('user_message_info.id'))
    to_legislators = db.relationship('MessageLegislator', backref='message')

    # email uid from postmark
    email_uid = db.Column(db.String(1000))
    # for follow up email to enter in address information
    verification_token = db.Column(db.String(64), default=uid_creator('Message', 'verification_token'))
    # prevent a message from being sent more than once
    live_link = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    @property
    def email(self): return self.user_message_info.user.email
    @email.setter
    def email(self, value): self.user_message_info.user.email = value

    @property
    def prefix(self): return self.user_message_info.prefix
    @prefix.setter
    def prefix(self, value): self.user_message_info.prefix = value

    @property
    def first_name(self): return self.user_message_info.first_name
    @first_name.setter
    def first_name(self, value): self.user_message_info.first_name = value

    @property
    def last_name(self): return self.user_message_info.last_name
    @last_name.setter
    def last_name(self, value): self.user_message_info.last_name = value

    @property
    def street_address(self): return self.user_message_info.street_address
    @street_address.setter
    def street_address(self, value): self.user_message_info.street_address = value

    @property
    def street_address2(self): return self.user_message_info.street_address2
    @street_address2.setter
    def street_address2(self, value): self.user_message_info.street_address2 = value

    @property
    def city(self): return self.user_message_info.city
    @city.setter
    def city(self, value): self.user_message_info.city = value

    @property
    def state(self): return self.user_message_info.state
    @state.setter
    def state(self, value): self.user_message_info.state = value

    @property
    def zip5(self): return self.user_message_info.zip5
    @zip5.setter
    def zip5(self, value): self.user_message_info.zip5 = value

    @property
    def zip4(self): return self.user_message_info.zip4
    @zip4.setter
    def zip4(self, value): self.user_message_info.zip4 = value

    @property
    def phone_number(self): return self.user_message_info.phone_number
    @phone_number.setter
    def phone_number(self, value): self.user_message_info.phone_number = value

    def verification_link(self, path=None):
        """
        Gets the verification link URI string for this message.

        @param path: validation url from view
        @type path: string
        @return: URL for confirmation email
        @rtype: string
        """
        return settings.BASE_URL + (path if path is not None else '/validate/' + self.verification_token) + \
            '?' + urllib.urlencode({'email': self.user_message_info.user.email})

    def set_legislators(self, legislators):
        """
        Used to set which legislators that this message will be sent to

        @param legislators: single or list of legislators
        @type legislators: list[models.Legislator or string]
        @return: True if success, False otherwise
        @rtype: boolean
        """
        if type(legislators) is not list: legislators = [legislators]

        try:
            self.to_legislators = [MessageLegislator(message_id=self.id,
                                                     legislator_id=(leg if type(leg) is str else leg.bioguide_id))
                                   for leg in legislators]
            db.session.commit()
            return True
        except:
            db.session.rollback()
            return False


    def add_legislators(self, legislators):
        """
        Add a legislator that this will message will be sent to

        @param legislators: single or list of legislators
        @type legislators: list[models.Legislator or string]
        @return: True if success, False otherwise
        @rtype: boolean
        """
        if type(legislators) is not list: legislators = [legislators]

        try:
            for leg in legislators:
                db_first_or_create(MessageLegislator,
                                   message_id=self.id,
                                   legislator_id=(leg if type(leg) is str else leg.bioguide_id))
            return True
        except:
            return False


    def get_legislators(self, as_dict=False):
        """
        Retrieves the legislator models to which this message is to be sent.

        @param as_dict:  if True, the method will return a dictionary with bioguide_ids as keys. False = list
        @type as_dict: dict
        @return: legislators for this message
        @rtype: list[models.Legislator] or dict[string:models.Legislator]
        """
        if as_dict:
            toReturn = {}
            for leg in self.to_legislators:
                l = Legislator.query.filter_by(bioguide_id=leg.legislator_id).first()
                toReturn[l.bioguide_id] = l
            return toReturn
        else:
            return Legislator.query.join(MessageLegislator).filter(
                MessageLegislator.id.in_([ml.id for ml in self.to_legislators])).all()

    def get_send_status(self):
        target_count = len(self.to_legislators)
        sent_count = MessageLegislator.query.join(Message).filter(Message.id == self.id,
                                                                  MessageLegislator.sent.is_(True)).count()
        if sent_count == 0:
            return 'unsent'
        elif sent_count < target_count:
            return 'sundry'
        else:
            return 'sent'

    def associate_legislators(self, force=False):
        if force or not self.to_legislators:
            self.set_legislators(self.user_message_info.members_of_congress)

    def send(self, fresh=False):
        """
        Attempts to the send this message using phantom on the capitol.

        @return: list of MessageLegislator instances that were processed
        @rtype: list[models.MessageLegislator]
        """
        newly_sent = []
        for msg_leg in self.to_legislators:
            try:
                newly_sent.append(msg_leg.send())
            except:
                continue
        return newly_sent if fresh else self.to_legislators

    def map_to_contact_congress_fields(self):
        """
        Converts model data into a dictionary for phantom of the capitol.

        @return: dictionary of values
        @rtype: dict
        """
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

    class Analytics():

        def __init__(self):
            self.today = datetime.datetime.today()
            self.today_start = self.today.replace(hour=0, minute=0, second=0, microsecond=0)

        def total_messages(self):
            return Message.query.count()

        def new_messages_today(self):
            return self.new_users_last_n_days(0)

        def new_messages_last_n_days(self, n_days):
            return User.query.filter(User.created_at > (self.today_start - datetime.timedelta(days=n_days))).count()

        def new_users_range(self, start_days, end_days):
            return User.query.filter(and_(User.created_at > (self.today_start - datetime.timedelta(days=start_days)),
                                   User.created_at < (self.today_start - datetime.timedelta(days=end_days)))).count()

        def growth_rate(self, n_days):
            last_n = float(self.new_users_last_n_days(n_days))
            prev_last_n = float(self.new_users_range(n_days*2, n_days))
            return (last_n - prev_last_n) / last_n

        def users_with_verified_districts(self):
            return UserMessageInfo.query.join(User).filter(
                and_(UserMessageInfo.default.is_(True), not_(UserMessageInfo.district.is_(None)))).count()

class MessageLegislator(db.Model):

    class ModelView(MyModelView):
        column_searchable_list = ['send_status']

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.String(7), db.ForeignKey('legislator.bioguide_id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    send_status = db.Column(db.String(4096), default='{"status": "unsent"}') # stringified JSON
    sent = db.Column(db.Boolean, nullable=True, default=None)

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    def is_sent(self):
        return self.sent

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
        """
        Method that actually passes information to phantom of the capitol.

        @return: self
        @rtype: models.MessageLegislator
        """
        if not self.is_sent():

            for bioguide_id, ra in phantom_on_the_capitol.retrieve_form_elements([self.legislator.bioguide_id]).iteritems():
                json_dict = self.map_to_contact_congress()

                for step in ra['required_actions']:
                    field = step.get('value')
                    options = step.get('options_hash')
                    if options is not None:
                        # convert first to dictionary for convenience
                        if type(options) is not dict:
                            options = {k: k for k in options}
                        if field == '$TOPIC':
                            # need lower case strings for select-solver
                            options = {k.lower(): v for k, v in options.items()}
                            try:  # try to determine best topic based off content of text
                                choice = Topic.topic_for_message(options.keys(), self.message)
                                json_dict['fields'][field] = choice
                                self.topic = Topic.query.filter_by(name=choice).first()
                            except:  # if failed, choose a random topic
                                pass
                        if field not in json_dict['fields'] or json_dict['fields'][field] not in options.values():
                            json_dict['fields'][field] = random.choice(options.values())
                    if field not in json_dict['fields'].keys():
                        print 'What the heck is ' + step.get('value') + ' in ' + bioguide_id + '?'
                result = phantom_on_the_capitol.fill_out_form(json_dict)
                self.sent = result['status'] == 'success'
                self.send_status = json.dumps(result)
            db.session.commit()
            return self

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