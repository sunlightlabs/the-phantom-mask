import requests
from config import settings

def choose(text, choices, retry=0):
    try:
        if retry > 3:
            return False

        params = {
            'text': text,
            'choices': (','.join(choices)).lower()
        }

        r = requests.get(settings.SELECT_SOLVER_BASE + '/choose.json', params=params)

        if "Internal Server Error" in r.text:
            return None

        return r.text.replace('"','')
    except:
        return choose(text, choices, retry=retry+1)