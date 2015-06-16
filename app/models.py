from phantom_mask import db
from config import settings
from datetime import datetime, timedelta
import uuid
from contextlib import contextmanager
import urllib
import json
from lib import usps, phantom_on_the_capitol, select_solver
import random
from dateutil import parser
import pytz
from lib.int_ext import ordinal
from services import determine_district_service, address_inferrence_service, geolocation_service
from lib.dict_ext import sanitize_keys
from sqlalchemy import or_, and_, not_
from flask import url_for, flash
import jellyfish
import sys
from flask.ext.login import UserMixin
import flask_login
from flask_admin.contrib.sqla import ModelView
from jinja2 import Markup
from flask import jsonify, redirect, request
from sqlalchemy import func
from helpers import app_router_path
from sqlalchemy_utils.functions import get_class_by_table
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from flask_admin import expose
from util import render_without_request
from helpers import render_template_wctx, append_get_params
from flask_wtf import Form



import os

@contextmanager
def get_db_session():
    try:
        yield db.session
    finally:
        db.session.remove()


def set_attributes(model, attrs, commit=False):
    for k, v in attrs:
        try:
            setattr(model, k, v)
        except:
            continue
    if commit:
        db.session.commit()
    return model


def db_del_and_commit(model, commit=True):
    try:
        db.session.delete(model)
        if commit:
            db.session.commit()
        return True
    except:
        db.session.rollback()
        return None

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

    form_base_class = Form

    def _handle_view(self, name, **kwargs):
        if name != 'login' and not self.is_accessible():
            return redirect(url_for('admin.login', next=request.url))

    def is_accessible(self):
        return flask_login.current_user.is_authenticated()




class MyBaseModel(db.Model):

    __abstract__ = True

    def __repr__(self):
        return str([(col.name, getattr(self,col.name)) for col in self.__table__.columns])

    @property
    def json(self):
        return to_json(self, self.__class__)




class BaseAnalytics(object):

    def __init__(self, model):
        self.model = model
        self.today = datetime.today()
        self.today_start = self.today.replace(hour=0, minute=0, second=0, microsecond=0)

    def total_count(self):
        return self.model.query.count()

    def new_today(self):
        return self.new_last_n_days(0)

    def new_last_n_days(self, n_days):
        return self.model.query.filter(self.model.created_at > (self.today_start - timedelta(days=n_days))).count()

    def new_in_range(self, start_days, end_days):
        return self.model.query.filter(and_(self.model.created_at > (self.today_start - timedelta(days=start_days)),
                               self.model.created_at < (self.today_start - timedelta(days=end_days)))).count()

    def growth_rate(self, n_days):
        last_n = float(self.new_last_n_days(n_days))
        prev_last_n = float(self.new_in_range(n_days*2, n_days))
        return (last_n - prev_last_n) / last_n





class Legislator(MyBaseModel):
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

    FIPS_CODES = {
        "AK": "02",
        "AL": "01",
        "AR": "05",
        "AS": "60",
        "AZ": "04",
        "CA": "06",
        "CO": "08",
        "CT": "09",
        "DC": "11",
        "DE": "10",
        "FL": "12",
        "GA": "13",
        "GU": "66",
        "HI": "15",
        "IA": "19",
        "ID": "16",
        "IL": "17",
        "IN": "18",
        "KS": "20",
        "KY": "21",
        "LA": "22",
        "MA": "25",
        "MD": "24",
        "ME": "23",
        "MI": "26",
        "MN": "27",
        "MO": "29",
        "MS": "28",
        "MT": "30",
        "NC": "37",
        "ND": "38",
        "NE": "31",
        "NH": "33",
        "NJ": "34",
        "NM": "35",
        "NV": "32",
        "NY": "36",
        "OH": "39",
        "OK": "40",
        "OR": "41",
        "PA": "42",
        "PR": "72",
        "RI": "44",
        "SC": "45",
        "SD": "46",
        "TN": "47",
        "TX": "48",
        "UT": "49",
        "VA": "51",
        "VI": "78",
        "VT": "50",
        "WA": "53",
        "WI": "55",
        "WV": "54",
        "WY": "56"
    }

    @staticmethod
    def humanized_district(state, district):
        return (ordinal(int(district)) if int(district) > 0 else 'At-Large') + ' Congressional district of ' + usps.CODE_TO_STATE.get(state)

    @staticmethod
    def humanized_state(state):
        return usps.CODE_TO_STATE.get(state)

    @staticmethod
    def get_district_geojson_url(state, district):
        try:
            fips = Legislator.FIPS_CODES.get(state)
            return "http://realtime.influenceexplorer.com/geojson/cd113_geojson/%s%0*d.geojson" % (fips, 2, int(district))
        except:
            return None

    @classmethod
    def members_for_state_and_district(cls, state, district, contactable=None):
        or_seg = or_(Legislator.district.is_(None), Legislator.district == district)
        and_seg = [Legislator.state == state, or_seg]
        if contactable is not None:
            query = and_(Legislator.contactable.is_(contactable), *and_seg)
        else:
            query = and_(*and_seg)

        return Legislator.query.filter(query).all()

        """

        return Legislator.query.filter(and_(Legislator.contactable.is_(True), Legislator.state == self.state,
                 or_(Legislator.district.is_(None), Legislator.district == self.district))).all()
        """

    @classmethod
    def congress_api_columns(cls):
        return [col.name for col in cls.__table__.columns if 'official' in col.info and col.info['official']]

    @classmethod
    def get_leg_buckets_from_emails(self, permitted_legs, emails):
        legs = {label: [] for label in ['contactable','non_existent','uncontactable','does_not_represent']}
        inbound_emails = [email_addr for email_addr in emails]

        # user sent to catchall address
        if settings.CATCH_ALL_MYREPS in inbound_emails:
            legs['contactable'] = permitted_legs
            inbound_emails.remove(settings.CATCH_ALL_MYREPS)

        # maximize error messages for users for individual addresses
        for recip_email in inbound_emails:
            leg = Legislator.query.filter(func.lower(Legislator.oc_email) == func.lower(recip_email)).first()
            if leg is None:
                legs['non_existent'].append(recip_email)  # TODO refer user to index page?
            elif not leg.contactable:
                legs['uncontactable'].append(leg)
            elif leg not in permitted_legs:
                legs['does_not_represent'].append(leg)
            elif leg not in legs['contactable']:
                legs['contactable'].append(leg)
            else:
                continue

        return legs

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



class AdminUser(MyBaseModel, UserMixin):

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


class Token(MyBaseModel):

    token = db.Column(db.String(64), unique=True, primary_key=True)
    item_id = db.Column (db.Integer)
    item_table = db.Column(db.String(16))

    @classmethod
    def convert_token(cls, token):
        msg, umi, user = None, None, None
        token = cls.query.filter_by(token=token).first()
        if token is not None:
            item = token.item
            if type(item) is User:
                user = item
                umi = user.default_info
            elif type(item) is Message:
                msg = item
                umi = msg.user_message_info
                user = umi.user

        return msg, umi, user

    @classmethod
    def uid_creator(cls, model=None, param='token'):
        """
        Creates a potential 64 character string uid, checks for collisions in input class,
        and returns a uid.

        @return: 64 character alphanumeri c string
        @rtype: string
        """
        model = model if model is not None else cls
        while True:
            potential_token = uuid.uuid4().hex + uuid.uuid4().hex
            if model.query.filter_by(**{param: potential_token}).count() == 0:
                return potential_token

    @property
    def item(self):
        return get_class_by_table(db.Model, db.Model.metadata.tables[self.item_table]).query.filter_by(id=self.item_id).first()

    @item.setter
    def item(self, item):
        self.item_id = item.id
        self.item_table = item.__table__.name

    def __init__(self, item, **kwargs):
        super(Token, self).__init__(**kwargs)
        self.token = self.uid_creator()
        self.item = item

    def reset(self, token=None):
        self.token = token if token is not None else self.uid_creator()
        db.session.commit()
        return self.token

    def link(self):
        """
        Gets the url for this token.

        @param path: validation url from view
        @type path: string
        @return: URL for confirmation email
        @rtype: string
        """
        return app_router_path('update_user_address', token=self.token)

class HasTokenMixin(db.Model):

    __abstract__ = True

    __mapper_args__ = {
        'batch' : False
    }

    @property
    def token(self):
        return Token.query.filter_by(item_id=self.id, item_table=self.__table__.name).first()

    @token.setter
    def token(self, token):
        self.token = token

    def verification_link(self):
        return self.token.link()


class User(MyBaseModel, HasTokenMixin):

    class ModelView(MyModelView):
        
        column_searchable_list = ['email', 'tmp_token']

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_infos = db.relationship('UserMessageInfo', backref='user')
    role = db.Column(db.Integer, default=0)
    tmp_token = db.Column(db.String(64), unique=True)

    ROLES = {
        0: 'user',
        1: 'special',
        2: 'admin'
    }

    @classmethod
    def global_captcha(cls):
        return Message.query.filter((datetime.now() - timedelta(hours=settings.USER_MESSAGE_LIMIT_HOURS)
                                    < Message.created_at)).count() > settings.GLOBAL_HOURLY_CAPTCHA_THRESHOLD

    def __html__(self):
        return render_without_request('snippets/user.html', user=self)

    @property
    def default_info(self):
        return UserMessageInfo.query.filter_by(user_id=self.id, default=True).first()

    def set_tmp_token(self, token):
        self.tmp_token = token
        db.session.commit()
        return self.tmp_token

    def create_tmp_token(self):
        self.set_tmp_token(Token.uid_creator(self, 'tmp_token'))

    def kill_tmp_token(self):
        self.set_tmp_token(None)

    def tmp_token_link(self):
        return settings.BASE_URL + app_router_path('new_token', token=self.tmp_token)

    def get_role(self):
        return self.ROLES.get(self.role, 'unknown')

    def is_admin(self):
        return self.ROLES.get(self.role) is 'admin'

    def is_special(self):
        return self.ROLES.get(self.role) is 'special'

    def can_skip_rate_limit(self):
        return self.is_admin() or self.is_special()

    def get_rate_limit_status(self):
        """
        Determines if a user should be rate limited (or blocked if argument provided

        @return status of rate limit [block, captcha, free]
        @rtype string
        """

        if self.can_skip_rate_limit():
            return 'free'

        if User.global_captcha():
            return 'g_captcha'

        count = self.messages().filter((datetime.now() - timedelta(hours=settings.USER_MESSAGE_LIMIT_HOURS) < Message.created_at)).count()
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

    def address_change_link(self):
        return self.token.link()

    class Analytics(BaseAnalytics):

        def __init__(self):
            super(User.Analytics, self).__init__(User)

        def users_with_verified_districts(self):
            return UserMessageInfo.query.join(User).filter(
                and_(UserMessageInfo.default.is_(True), not_(UserMessageInfo.district.is_(None)))).count()


class UserMessageInfo(MyBaseModel):

    class ModelView(MyModelView):
        column_searchable_list = ['first_name', 'last_name', 'street_address', 'street_address2', 'city', 'state',
                                  'zip5', 'zip4', 'phone_number']

    # meta data
    id = db.Column(db.Integer, primary_key=True)
    default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

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

    @classmethod
    def first_or_create(cls, user_id, created_at=datetime.now, **kwargs):
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
        return Legislator.humanized_district(self.state, self.district)

    def humanized_state(self):
        return Legislator.humanized_state(self.state)

    def should_update_address_info(self):
        """
        Determines if user needs to update their address information.

        @return: True if they need to update, False otherwise
        @rtype: boolean
        """
        return self.accept_tos is None or (datetime.now() - self.accept_tos).days >= settings.ADDRESS_DAYS_VALID

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
                self.latitude, self.longitude = geolocation_service.geolocate(street_address=self.street_address,
                                                                              city=self.city,
                                                                              state=self.state,
                                                                              zip5=self.zip5)
                db.session.commit()
                return self.latitude, self.longitude
            except:
                return None, None

    def get_district_geojson_url(self):
        return Legislator.get_district_geojson_url(self.state, self.district)

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

        data = determine_district_service.determine_district(zip5=self.zip5)
        if data is None:
            self.geolocate_address()
            data = determine_district_service.determine_district(latitude=self.latitude, longitude=self.longitude)

        try:
            self.district = data.get('district')
            self.state = data.get('state')
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


class Topic(MyBaseModel):

    class ModelView(MyModelView):
        column_searchable_list = ['name']

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), unique=True)
    wikipedia_parent = db.Column(db.Integer, db.ForeignKey('topic.id'))
    msg_legs = db.relationship('MessageLegislator', backref='topic')

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

class Message(MyBaseModel, HasTokenMixin):

    class ModelView(MyModelView):

        column_list = ('created_at', 'subject', 'user_message_info', 'to_legislators', 'status')
        column_searchable_list = ['to_originally', 'subject', 'msgbody']

        def scaffold_form(self):
            from wtforms import SelectMultipleField
            form_class = super(Message.ModelView, self).scaffold_form()
            form_class.legislators = SelectMultipleField('Add Legislators', choices=[(x.bioguide_id, x.bioguide_id) for x in Legislator.query.all()])
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
    created_at = db.Column(db.DateTime, default=datetime.now)
    to_originally = db.Column(db.String(8000)) # original recipients from email as json list
    subject = db.Column(db.String(500))
    msgbody = db.Column(db.String(8000))

    user_message_info_id = db.Column(db.Integer, db.ForeignKey('user_message_info.id'))
    to_legislators = db.relationship('MessageLegislator', backref='message')

    # email uid from postmark
    email_uid = db.Column(db.String(1000))
    # None = sent, free = able to be sent, (g_)captcha = must solve captcha to send, block = can't send
    status = db.Column(db.String(10), nullable=True, default='free')


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

    def free_link(self):
        set_attributes(self, {'status': 'free'}.iteritems(), commit=True)

    def kill_link(self):
        set_attributes(self, {'status': None}.iteritems(), commit=True)

    def update_status(self):
        self.status = self.user_message_info.user.get_rate_limit_status()
        db.session.commit()

    def needs_captcha_to_send(self):
        return self.status in ['captcha', 'g_captcha']

    def is_free_to_send(self):
        return self.status == 'free'

    def is_already_sent(self):
        return self.status is None

    def queue_to_send(self, moc=None):
        from scheduler import send_to_phantom_of_the_capitol
        set_attributes(self, {'status': None}.iteritems(), commit=True)
        if moc is not None: self.set_legislators(moc)
        send_to_phantom_of_the_capitol.delay(self.id)
        return True

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
            super(Message.Analytics, self).__init__(Message)


class MessageLegislator(MyBaseModel):

    class ModelView(MyModelView):
        column_searchable_list = ['send_status']

        column_list = ('id', 'sent', 'send_status', 'topic', 'legislator', 'message', 'message.user_message_info')

        @expose('/sent/', methods=['GET', 'POST'])
        def sent_view(self):
            model = self.get_one(request.args.get('id', None))
            if model is None or model.sent:
                return redirect(self.get_url('.index_view'))
            from scheduler import send_to_phantom_of_the_capitol
            send_to_phantom_of_the_capitol.delay(msgleg_id=model.id)
            flash('Message %s will attempt to be resent' % str(model.id))
            return redirect(self.get_url('.index_view'))

        def _sent_formatter(view, context, model, name):
            if not model.sent:
                ctx = {'msgleg-id': str(model.id)}
                get_paramss = {'url': view.url, 'id': ctx['msgleg-id']}
                ctx['post_url'] = append_get_params(view.url + '/' + name + '/', **get_paramss)
                return Markup(render_template_wctx('admin/resend_button.html', context=ctx))
            else:
                return model.sent

        column_formatters = {
            'sent': _sent_formatter
        }


    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.String(7), db.ForeignKey('legislator.bioguide_id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    send_status = db.Column(db.String(4096), default='{"status": "unsent"}') # stringified JSON
    sent = db.Column(db.Boolean, nullable=True, default=None)

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


for cls in HasTokenMixin.__subclasses__():

    @event.listens_for(cls, 'after_insert')
    def receive_after_insert(mapper, connection, target):
        db.session.add(Token(item=target))

    @event.listens_for(cls, 'after_delete')
    def receive_after_delete(mapper, connection, target):
        db.session.delete(target.token)