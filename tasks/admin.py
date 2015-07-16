import os
import sys
import requests
import uuid

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from config import settings
from app.phantom_mask import db
from daily import import_congresspeople
from monthly import import_topics
import traceback
import string
import random
import json


def reset_database(prompt=True):
    if prompt is True:
        decision = raw_input("This will delete everything in the database. Are you sure you want to do this? [Y,n] ")
        decision2 = raw_input("Are you absolutely sure? This can not be undone... [Y,n] ")
    else:
        decision = decision2 = 'Y'

    if decision == 'Y' and decision2 == 'Y':
        try:
            print 'Dropping all tables and recreating them from scratch...'
            db.drop_all()
            db.create_all()
            import_data()
        except:
            print traceback.format_exc()
    else:
        print "Aborting resetting database."


def import_data():
    print 'Importing congresspeople...'
    import_congresspeople(from_cache=True)
    print "Importing topics. This may take a while..."
    import_topics(from_cache=True)


def create_test_data():
    try:
        from app.models import Topic
        from tests.factories import user, user_message_info, message, admin_user

        user1 = user(email='cdunwell@sunlightfoundation.com')
        umi1 = user_message_info(user=user1, info={
            'default': True,
            'prefix': 'Mr.',
            'first_name': 'Clayton',
            'last_name': 'Dunwell',
            'street_address': '2801 Quebec St NW',
            'street_address2': '',
            'city': 'Washington',
            'state': 'DC',
            'zip5': '20008',
            'phone_number': '2025551234'
        })
        msg1_1 = message(umi=umi1)
        msg1_2 = message(umi=umi1)


        user2 = user(email='ocheng@sunlightfoundation.com')
        umi2 = user_message_info(user=user2)
        msg2 = message(umi=umi2)


        for i in range(0,100):
            user(email=(''.join(random.choice(string.ascii_lowercase) for _ in range(10)))+'@example.com')

        admin1 = admin_user()

    except:
        print traceback.format_exc()


def setup_test_environment():
    reset_database(False)
    create_test_data()


def simulate_postmark_message(from_email, to_emails=None, messageid=None):

    if from_email not in settings.ADMIN_EMAILS:
        return from_email + " not in admin emails: " + str(settings.ADMIN_EMAILS)

    messageid = uuid.uuid4().hex if messageid is None else messageid
    if to_emails is None:
        to_emails = [{'Email': 'Rep.Johnboehner@opencongress.org'}]
    elif type(to_emails) is str:
        to_emails = [{'Email': to_emails}]
    elif type(to_emails) is list:
        to_emails = [{'Email': te} for te in to_emails]
    else:
        raise Exception('Bad input')

    params = {
        'Subject': 'Thank you!',
        'TextBody': "Thank you for everything that you do!",
        'Date': 'Thu, 5 Apr 2014 16:59:01 +0200',
        'MessageID': messageid,
        "FromFull": {
            "Email": from_email,
            "Name": "John Smith",
        },
        "ToFull": to_emails
    }
    try:
        req = requests.post(settings.BASE_PROTOCOL + settings.BASE_URL + '/postmark/inbound',
                            data=json.dumps(params),
                            headers={"content-type": "text/javascript"})
        print req.json()
        return req.json()
    except:
        print 'Request to postmark inbound url failed'


def reset_tos(from_email):
    from app.models import User
    try:
        u = User.query.filter_by(email=from_email).first()
        u.accept_tos = None
        map(lambda msg: setattr(msg, 'status', 'free'), u.messages().all())
        db.session.commit()
    except:
        print 'User with email ' + from_email + ' does not exist.'


if __name__ == '__main__':
    tasks = {
        'reset_database': reset_database,
        'create_test_data': create_test_data,
        'setup_test_environment': setup_test_environment,
        'simulate_postmark_message': simulate_postmark_message,
        'reset_tos': reset_tos
    }

    if len(sys.argv) > 1:
        try:
            tasks.get(sys.argv[1])(*sys.argv[2:])
        except:
            print 'Admin task with name "' + sys.argv[1] + '" does not exist. Choices are: ' + str(tasks.keys())
    else:
        print 'Please provide an admin task to run with relevant arguments. ' + str(tasks.keys())