import re
import requests

requests.packages.urllib3.disable_warnings()

CODE_TO_STATE = {
    'WA': 'Washington', 'WI': 'Wisconsin', 'WV': 'West Virginia',
    'FL': 'Florida', 'FM': 'Federated States of Micronesia',
    'WY': 'Wyoming', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'NE': 'Nebraska', 'NY': 'New York', 'RI': 'Rhode Island',
    'NV': 'Nevada', 'GU': 'Guam', 'CO': 'Colorado',
    'CA': 'California', 'GA': 'Georgia', 'CT': 'Connecticut',
    'OK': 'Oklahoma', 'OH': 'Ohio', 'KS': 'Kansas', 'SC': 'South Carolina',
    'KY': 'Kentucky', 'OR': 'Oregon', 'SD': 'South Dakota', 'DE': 'Delaware',
    'DC': 'District of Columbia', 'HI': 'Hawaii', 'PR': 'Puerto Rico',
    'PW': 'Palau', 'TX': 'Texas', 'LA': 'Louisiana', 'TN': 'Tennessee',
    'PA': 'Pennsylvania', 'AA': 'Armed Forces Americas', 'VA': 'Virginia',
    'AE': 'Armed Forces Middle East', 'VI': 'Virgin Islands', 'AK': 'Alaska',
    'AL': 'Alabama', 'AP': 'Armed Forces Pacific', 'AS': 'American Samoa',
    'AR': 'Arkansas', 'VT': 'Vermont', 'IL': 'Illinois', 'IN': 'Indiana',
    'IA': 'Iowa', 'AZ': 'Arizona', 'ID': 'Idaho', 'ME': 'Maine',
    'MD': 'Maryland', 'MA': 'Massachusetts', 'UT': 'Utah',
    'MO': 'Missouri', 'MN': 'Minnesota', 'MI': 'Michigan', 'MH': 'Marshall Islands',
    'MT': 'Montana', 'MP': 'Northern Mariana Islands', 'MS': 'Mississippi'
}

USPS_BASE_URL = 'https://tools.usps.com/go/ZipLookupResultsAction!input.action'

def usps_zip_lookup(street_address, city, state, z5=''):
    """
    Use usps to look up zip5 and zip4
    @param street_address: [String] street address
    @param city: [String] city name
    @param state: [String] state name
    @param zip: [String] zip5
    @return: [Tuple] (<(String\d{5}|None)>,<(String\d{4}|None)>)
    """

    # construct get parameters string
    params = {
        'resultMode': 0,
        'companyName': '',
        'address1': street_address,
        'address2': '',
        'city': city,
        'state': state,
        'urbanCode': '',
        'postalCode': '',
        'zip': z5
    }

    # make request. need to spoof headers or get infinite redirect
    r = requests.get(USPS_BASE_URL, params=params, verify=False,
                     headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.99 Safari/537.36'})

    # retrieve raw html
    html = r.text

    # try to extract zip5 and zip4 from HTML. Return None if can't be resolved.
    try: zip5 = re.sub("""<("[^"]*"|'[^']*'|[^'">])*>""",'',(re.search('<span class=\"zip\".*>\d{5}\<\/span\>', html)).group(0))
    except: zip5 = None
    try: zip4 = re.sub("""<("[^"]*"|'[^']*'|[^'">])*>""",'',(re.search('<span class=\"zip4\">\d{4}\<\/span\>', html)).group(0))
    except: zip4 = None

    return (zip5, zip4)