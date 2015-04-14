import os
import sys
import requests
import json

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from config import settings
from app.models import Legislator
from app.models import db
from app.models import set_attributes
from app.models import db_first_or_create
import traceback


def import_congresspeople(from_cache=False):
    """
    Imports all the congresspeople for whom there exists a contact form.

    @return:
    """
    if from_cache:  # load it from cache
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../' + settings.LEGISLATOR_DATA_CACHE, mode='r') as cachejson:
            data = json.load(cachejson)
            for leg in data:
                fields = {k: v for k, v in leg.items() if k in Legislator.congress_api_columns()}
                db_first_or_create(Legislator, commit=False, **fields)
            db.session.commit()

    contactable = requests.get(settings.PHANTOM_API_BASE + '/list-congress-members',
                               params={'debug_key': settings.PHANTOM_DEBUG_KEY})
    bioguide_ids = [x['bioguide_id'] for x in contactable.json()]

    # marks those for whom we don't have a contact-congress yaml as uncontactable
    for l in Legislator.query.all():
        if l.bioguide_id not in bioguide_ids:
            l.contactable = False
    db.session.commit()

    if not from_cache:
        # Create legislator entry for congresspeople for whom we don't have a database entry
        all_legislators = []
        for bgi in bioguide_ids:
            if Legislator.query.filter_by(bioguide_id=bgi).first() is None:
                try:
                    r = requests.get(settings.CONGRESS_API_BASE + '/legislators',
                                     params={'bioguide_id': bgi, 'apikey': settings.SUNLIGHT_API_KEY})
                    data = r.json()['results'][0]
                    all_legislators.append(data)
                    new = set_attributes(Legislator(), data.iteritems())
                    db.session.add(new)
                    db.session.commit()
                except:
                    print "No data from congress api for : " + bgi
                    continue

        # save data to cache in case we need to load it up again
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../' + settings.LEGISLATOR_DATA_CACHE, mode='w') as cachejson:
            json.dump(all_legislators, cachejson, indent=4)

if __name__ == '__main__':
    import_congresspeople()