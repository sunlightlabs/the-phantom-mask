import requests
from config import settings
import json

def retrieve_form_elements(args):
    """
    Obtain the steps needed to fill out the congressial webform of provided args

    @param args: [List<String>|Message]
    @return: [Dictionary|None]
    """
    if type(args) is list:
        bioguide_ids = args
    else:
        bioguide_ids = [x.bioguide_id for x in args.get_legislators()]

    try:
        steps = requests.post(settings.PHANTOM_API_BASE + '/retrieve-form-elements',
                              headers={"Content-Type": 'application/json'},
                              data=json.dumps({'bio_ids': bioguide_ids}))

        return steps.json()
    except:
        print 'Failed to obtain steps.'
        return None

def fill_out_form(json_dict):
    """
    Attempts to fill out the congressial webform with input json data.

    @param json_dict: dictionary to be converted into a json string. Example of input schema:
                      {"bio_id": "A000000",
                       "fields": {
                            "$NAME_FIRST": "John",
                            "$NAME_LAST": "Doe",
                            "$ADDRESS_STREET": "123 Main Street",
                            "$ADDRESS_CITY": "New York",
                            "$ADDRESS_ZIP5": "10112",
                            "$EMAIL": "joe@example.com",
                            "$MESSAGE": "I have concerns about the proposal....",
                            "$NAME_PREFIX": "Grand Moff"
                            }
                      }
    @return:
    """
    try:
        r = requests.post(settings.PHANTOM_API_BASE + '/fill-out-form',
                          headers={"Content-Type": 'application/json'},
                          data=json.dumps(json_dict))

        return r.json()
    except:
        print 'Failed to execute API call to phantom of the capitol.'
        return None