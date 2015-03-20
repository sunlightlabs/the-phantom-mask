import os
import sys
import requests

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from config import settings
from models import Legislator
from models import db
from models import set_attributes

CONGRESS_API_BASE = "http://congress.api.sunlightfoundation.com"
PHANTOM_API_BASE = "http://localhost:9292"

def import_congresspeople():
    """
    Imports all the congresspeople for whom there exists a contact form.

    @return:
    """

    contactable = requests.get(PHANTOM_API_BASE + '/list-congress-members',
                               params={'debug_key': settings.PHANTOM_DEBUG_KEY})

    bioguide_ids = [x['bioguide_id'] for x in contactable.json()]

    # marks those for whom we don't have a contact-congress yaml as uncontactable
    for l in Legislator.query.all():
        if l.bioguide_id not in bioguide_ids:
            l.contactable = False
    db.session.commit()

    # Create legislator entry for congresspeople for whom we don't have a database entry
    for bgi in bioguide_ids:
        if Legislator.query.filter_by(bioguide_id=bgi).first() is None:
            try:
                r = requests.get(CONGRESS_API_BASE + '/legislators', params={'bioguide_id': bgi,
                                                                             'apikey': settings.SUNLIGHT_API_KEY})
                new = set_attributes(Legislator(),r.json()['results'][0].iteritems())
                db.session.add(new)
                db.session.commit()
            except:
                print "No data from congress api for : " + bgi
                continue


def get_oc_email(bioguide_id):
    r = requests.get(CONGRESS_API_BASE + '/legislators', params={'bioguide_id': bioguide_id,
                                                                 'apikey': settings.SUNLIGHT_API_KEY})
    try:
        return r.json()['results'][0]['oc_email']
    except:
        return None

if __name__ == '__main__':
    import_congresspeople()