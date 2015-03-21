from app import db
import datetime
import uuid
from threading import Thread
import requests
import time
from config.settings import PHANTOM_API_BASE
from contextlib import contextmanager

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

    def title(self):
        return {
            'senate' : 'Sen.',
            'house' : 'Rep.',
        }.get(self.chamber, 'house')

    def title_and_last_name(self):
        return self.title() + " " + self.last_name

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256))

    user_infos = db.relationship('UserMessageInfo', backref='user')

class UserMessageInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

class Message(db.Model):
    """
    Stores message information from email
    """
    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.datetime.now)
    subject = db.Column(db.String(256))
    body = db.Column(db.String(8000))

    user_message_info_id = db.Column(db.Integer, db.ForeignKey('user_message_info.id'))

    to_legislators = db.relationship('MessageLegislator', backref='message')

    email_uid = db.Column(db.String(1000))
    # for follow up email to enter in address information
    verification_token = db.Column(db.String(32), default=uuid.uuid4().hex)

    def verification_link(self):
        return 'http://smokehouse.sunlightlabs.org/contact_congress/verify/' + self.verification_token

    def get_legislators(self):
        return [Legislator.query.filter_by(bioguide_id=leg.legislator_id).first() for leg in self.to_legislators]

    def send(self):

        legs = MessageLegislator.query.filter_by(message_id=self.id)

        for msgleg in legs:
            print "attempting to fill out form..."
            msgleg.fill_out_form()

    #def __repr__(self):
    #    return '<User %r>' % (self.name)

class MessageLegislator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.Integer, db.ForeignKey('legislator.bioguide_id'))
    send_status = db.Column(db.String(25), default='unsent')

    def fill_out_form(self):
        with get_db_session():
            headers = {'Content-Type': 'application/json'}
            reply = requests.post(PHANTOM_API_BASE + '/fill-out-form',
                                  headers=headers,
                                  data='{"bio_id": "A111111", "campaign_tag": "stop_sopa", "fields": {"$NAME_FIRST": "John", "$NAME_LAST": "Doe", "$ADDRESS_STREET": "123 Main Street", "$ADDRESS_CITY": "New York", "$ADDRESS_ZIP5": "10112", "$EMAIL": "joe@example.com", "$MESSAGE": "I have concerns about the proposal....", "$NAME_PREFIX": "Grand Moff"}}')
            data = reply.json()

            self.send_status = data['status']
            print self.send_status
        db.session.commit()
        db.session.close()

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

