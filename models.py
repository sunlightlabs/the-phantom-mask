from app import db
import datetime
import uuid

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

class Message(db.Model):
    """
    Stores message information from email
    """
    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.datetime.now)
    from_email = db.Column(db.String(256))
    subject = db.Column(db.String(256))
    body = db.Column(db.String(8000))

    to_legislators = db.relationship('MessageLegislator', backref='message', lazy='dynamic')

    email_uid = db.Column(db.String(1000))
    # for follow up email to enter in address information
    verification_token = db.Column(db.String(32), default=uuid.uuid4().hex)

    #def __repr__(self):
    #    return '<User %r>' % (self.name)

class MessageLegislator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    legislator_id = db.Column(db.Integer, db.ForeignKey('legislator.bioguide_id'))
    send_status = db.Column(db.String(25), default='unsent')

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

