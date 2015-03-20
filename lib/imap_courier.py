import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from imaplib import IMAP4, IMAP4_SSL
from config import settings
from models import Legislator
from models import Message
from models import MessageLegislator
import email
from email.parser import Parser
from email.utils import parseaddr
from email.utils import getaddresses
from sqlalchemy import func
from models import db
from dateutil.parser import parse

class Imap4EmailCourier():

    def __init__(self, server='', username='', password='', ssl=True):

        self.server = server
        self.username = username
        self.password = password
        self.ssl = ssl
        self.conn = None

    def connect(self, server='', username='', password='', ssl=True):
        if server != '': self.server = server
        if username != '': self.username = username
        if password != '': self.password = password

        self.conn = IMAP4_SSL(self.server) if self.ssl else IMAP4(self.server)
        self.conn.login(self.username, self.password)

    def requires_connection(self):
        func = self
        def check_connection_and_call(self, *args, **kwargs):
            if self.conn is None:
                raise Exception('Connection with server not made yet.')
            return func(self, *args, **kwargs)
        return check_connection_and_call

    @requires_connection
    def change_folder(self, folder):
        code, dummy = self.conn.select(folder)
        if code != 'OK': raise RuntimeError, "Failed to select inbox"
        return code

    @requires_connection
    def poll_messages(self, charset=None, *criteria):
        return self.conn.search(None, 'ALL' if not criteria else criteria)

    @requires_connection
    def fetch_all_messages(self):
        typ, data = self.poll_messages()
        for num in data[0].split():
            yield self.fetch_message_data(num)

    @requires_connection
    def fetch_message_data(self, num):
        typ, data = self.conn.fetch(num, '(RFC822)')
        return data

    def parse_message_data(self, data):
        for response_part in data:
            if isinstance(response_part, tuple):
                return email.message_from_string(response_part[1])

    def get_basic_information(self, parsed_data):
        return {
            'uid': self._get_uid(parsed_data),
            'from': self._get_return_path(parsed_data),
            'to': self._get_to(parsed_data),
            'subject': self._get_subject(parsed_data),
            'body': self._get_body(parsed_data),
            'date': self._get_date(parsed_data),
        }

    def get_from_parsed_data(self, parsed_data, attr):
        return {
            'to': self._get_to,
            'Return-Path': self._get_return_path,
            'body': self._get_body,
            'uid': self._get_uid,
            'subject': self._get_subject,
            'date': self._get_date,
        }.get(attr)(parsed_data)

    def _get_uid(self, parsed_data):
        return parsed_data.get('Message-ID')

    def _get_to(self, parsed_data):
        return getaddresses(parsed_data.get_all('to'))

    def _get_return_path(self, parsed_data):
        return parseaddr(parsed_data.get('Return-Path'))

    def _get_subject(self, parsed_data):
        return parsed_data.get('Subject')

    def _get_body(self, parsed_data):
        return parsed_data.get_payload().strip()

    def _get_date(self, parsed_data):
        return parsed_data.get('Date')




"""
courier = Imap4EmailCourier(settings.EMAIL_SERVER, settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
courier.connect()
courier.change_folder('inbound-forwarded')
parsed_data = courier.parse_message_data(courier.fetch_message_data(1))
print courier.get_basic_information(parsed_data)
"""

def get_all_messages():
    courier = Imap4EmailCourier(settings.EMAIL_SERVER, settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
    courier.connect()
    courier.change_folder('inbound-forwarded')
    messages_gen = courier.fetch_all_messages()
    for msg in messages_gen:
        parsed_data = courier.parse_message_data(msg)
        basic_data = courier.get_basic_information(parsed_data)
        if Message.query.filter_by(email_uid=basic_data.get('uid')).first() is None:
            new = Message(sent_at=parse(basic_data['date']),
                          from_email=basic_data['from'][1],
                          subject=basic_data['subject'],
                          body=basic_data['body'],
                          email_uid=basic_data['uid'])
            db.session.add(new)
            for person in basic_data['to']:
                leg = Legislator.query.filter(func.lower(Legislator.oc_email) == func.lower(person[1])).first()
                if leg is not None and leg.contactable:
                    ml = MessageLegislator(message_id=new.id, legislator_id=leg.bioguide_id)
                    db.session.add(ml)
                else:
                    print 'Not contactable'
                    pass # TODO send error message back to user
            db.session.commit()
        break


if __name__ == "__main__":
    get_all_messages()