import requests
from config import settings


def choose(text, choices):
    params = {
        'text': text,
        'choices': choices
    }

    r = requests.get(settings.SELECT_SOLVER_BASE + '/choose.json', params=params)

    print r.text