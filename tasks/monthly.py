import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from config import settings
from app.models import Topic
from app.models import db
from app.models import db_first_or_create


def import_topics(from_cache=False):

    Topic.query.delete()
    db.session.commit()

    if from_cache:
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../' + settings.TOPIC_DATA_CACHE, mode='r') as cachejson:
            data = json.load(cachejson)
            for topic in data:
                db_first_or_create(Topic, commit=False,
                                   name=topic['name'],
                                   wikipedia_parent=None if topic['wikipedia_parent'] == '' else topic['wikipedia_parent']
                                   )
            db.session.commit()

    if not from_cache:
        Topic.populate_topics_from_phantom_forms()
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../' + settings.TOPIC_DATA_CACHE, mode='w') as cachejson:
            json.dump([json.loads(t.json) for t in Topic.query.all()], cachejson, indent=4)