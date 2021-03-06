import sys
import os
import uuid
import json

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))


from app import models


def add_and_commit(factory):
    def create_model(*args, **kwargs):
        new = factory(*args, **kwargs)
        try:
            models.db.session.add(new)
            models.db.session.commit()
        except:
            models.db.session.rollback()
        return new
    return create_model

@add_and_commit
def user(email='john@example.com'):
    return models.User(email=email)

@add_and_commit
def message_legislator(msg, leg, send_status='{"status": "unsent"}', sent=None):
    return models.MessageLegislator(message=msg, legislator=leg, send_status=send_status, sent=sent)

@add_and_commit
def admin_user(username='admin', password='admin'):
    a = models.AdminUser(username=username)
    a.set_password(password)
    return a

@add_and_commit
def user_message_info(user, info=None):
    if info is None:
        info = {
            'default': True,
            'prefix': 'Mr.',
            'first_name': 'John',
            'last_name': 'Smith',
            'street_address': '69 Brown St.',
            'street_address2': 'Box 1234',
            'city': 'Providence',
            'state': 'RI',
            'zip5': '02912',
            'phone_number': '2025551234',
            'district': 1
        }
    umi = models.UserMessageInfo(user=user)
    for key, val in info.iteritems():
        try:
            setattr(umi, key, val)
        except:
            print "UserMessageInfo model doesn't have the attribute: " + key
    return umi

@add_and_commit
def message(umi, subject="Test subject", msgbody="Test message", to_originally=None):
    return models.Message(user_message_info=umi,
                          to_originally=json.dumps(to_originally if to_originally is not None else ['Rep.Aderholt@opencongress.org']),
                          subject=subject,
                          msgbody=msgbody,
                          email_uid=uuid.uuid4().hex)