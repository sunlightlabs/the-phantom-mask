import sys
import os
import uuid

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

import models

def add_and_commit(factory):
    def create_model(**kwargs):
        new = factory(**kwargs)
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
def message(umi, subject="Test subject", msgbody="Test message"):
    return models.Message(user_message_info=umi,
                          subject=subject,
                          msgbody=msgbody,
                          email_uid=uuid.uuid4().hex)