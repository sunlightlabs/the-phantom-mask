import requests
from bs4 import BeautifulSoup

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


def usps_request(**kwargs):

    # construct get parameters string
    params = {
        'resultMode': 0,
        'companyName': '',
        'address1': kwargs.get('street_address', ''),
        'address2': '',
        'city': kwargs.get('city', ''),
        'state': kwargs.get('state',''),
        'urbanCode': '',
        'postalCode': '',
        'zip': kwargs.get('zip5', '')
    }

    # make request. need to spoof headers or get infinite redirect
    return requests.get(USPS_BASE_URL, params=params, verify=False,
                        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.99 Safari/537.36'},
                        timeout=5)


def usps_address_lookup(**kwargs):

    # parse html
    soup = BeautifulSoup(usps_request(**kwargs).text)

    # get container div for results
    results_content = soup.find(id='results-content')

    # build return dict
    address = {
        'street_address': '',
        'city': '',
        'state': '',
        'zip5': '',
        'zip4': ''
    }

    try:
        address['street_address'] = str(results_content.find('span', class_='address1').text).strip()
    except:
        print "Can't find street address"
    try:
        address['city'] = str(results_content.find('span', class_='city').text).strip().title()
    except:
        print "Can't find city"
    try:
        address['state'] = str(results_content.find('span', class_='state').text).strip()
    except:
        print "Can't find state"
    try:
        address['zip5'] = str(results_content.find('span', class_='zip').text).strip()
    except:
        print "Can't find zip5"
    try:
        address['zip4'] = str(results_content.find('span', class_='zip4').text).strip()
    except:
        print "Can't find zip4"

    return address


def usps_zip_lookup(street_address, city, state, z5=''):
    """

    @param street_address: street address
    @type street_address: string
    @param city: city
    @type city: string
    @param state: state
    @type state: string
    @param z5: zip5
    @type z5: string
    @return: tuple of form (zip5, zip4)
    @rtype: tuple
    """

    address = usps_address_lookup(street_address=street_address, city=city, state=state, zip5=z5)
    return address['zip5'], address['zip4']