from app import db
import datetime
import uuid
from contextlib import contextmanager
from lib import phantom_on_the_capitol
import urllib
import json
from lib import usps
import random

@contextmanager
def get_db_session():
    try:
        yield db.session
    finally:
        db.session.remove()

def set_attributes(model, attrs):
    for k,v in attrs:
        try: setattr(model, k, v)
        except: continue
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
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    oc_email = db.Column(db.String(256))
    contactable = db.Column(db.Boolean, default=True)

    messages = db.relationship('MessageLegislator', backref='legislator', lazy='dynamic')

    @property
    def json(self):
        return to_json(self, self.__class__)

    def title(self):
        return {
            'senate' : 'Sen.',
            'house' : 'Rep.',
        }.get(self.chamber, 'house')

    def full_name(self):
        return self.first_name + " " + self.last_name

    def title_and_last_name(self):
        return self.title() + " " + self.last_name

    def title_and_full_name(self):
        return self.title() + " " + self.full_name()

    def image_url(self, size='small'):
        dimension = {
            'small': '225x275',
            'large': '450x550'
        }.get(size,'225x275')
        return "https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/" + dimension + "/" + self.bioguide_id + '.jpg'

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256))
    user_infos = db.relationship('UserMessageInfo', backref='user')

    @property
    def json(self):
        return to_json(self, self.__class__)

class UserMessageInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(32))
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    street_address = db.Column(db.String(1000))
    street_address2 = db.Column(db.String(1000))
    city = db.Column(db.String(256))
    state = db.Column(db.String(2))
    zip5 = db.Column(db.String(5))
    zip4 = db.Column(db.String(4))
    phone_number = db.Column(db.String(20))
    accept_tos = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    messages = db.relationship('Message', backref='user_message_info')

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

    def verification_link(self):
        """
        Generates the full verification link to this message.

        @return: [String] full url to verification link
        """
        return 'http://smokehouse.sunlightlabs.org/contact_congress/verify/' + self.verification_token + '?' + urllib.urlencode({'email':self.user_message_info.user.email})

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
        send_to = self.namespaced_to_legislators()
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
            '$ADDRESS_STATE_FULL': usps.CODE_TO_STATE.get(umi.state).lower().capitalize()
        }

    #def __repr__(self):
    #    return '<User %r>' % (self.name)

class MessageLegislator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.Integer, db.ForeignKey('legislator.bioguide_id'))
    send_status = db.Column(db.String(1024), default='{"status": "unsent"}') # stringified JSON

    def get_send_status(self):
        """
        Retrieves the current status of the message to the legislator.

        @return: [Dictionary] dictionary detailing the status of the message
        """
        try:
            return json.loads(self.send_status)
        except:
            return self.send_status

    def map_to_contact_congress(self):
        return {
            'bio_id': self.legislator.bioguide_id,
            'fields': self.message.map_to_contact_congress_fields()
        }

    @property
    def json(self):
        return to_json(self, self.__class__)

#def email_address_for_website(website):
#    pattern = re.compile("^(http[s]{0,1}\:\/\/)*(?:www[.])?([-a-z0-9]+)[.](house|senate)[.]gov\/.*", re.I)
#    if pattern.match(website):
#        o = urlparse.urlparse(website)
#        if o.netloc == '': return None
##        name = o.netlock.split('.')
#        if name[0] == 'www': name.pop(0)
#        print name

      #url = URI.parse(website)
      #return nil if url.host.nil?
      #match = pattern.match(url.host.downcase)
      #return nil if match.nil?
      #nameish, chamber = match.captures
      #prefix = (chamber.downcase == 'senate') ? 'Sen' : 'Rep'
      #return "#{prefix.capitalize}.#{nameish.capitalize}@#{Settings.email_congress_domain}"

