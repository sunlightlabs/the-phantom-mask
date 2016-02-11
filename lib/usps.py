import requests
from bs4 import BeautifulSoup

CODE_TO_STATE = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AS': 'American Samoa',
    'AZ': 'Arizona', 'AR': 'Arkansas', 'AA': 'Armed Forces Americas',
    'AE': 'Armed Forces Middle East', 'AP': 'Armed Forces Pacific',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
    'DE': 'Delaware', 'DC': 'District of Columbia',
    'FM': 'Federated States of Micronesia', 'FL': 'Florida',
    'GA': 'Georgia', 'GU': 'Guam', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MH': 'Marshall Islands',
    'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
    'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'MP': 'Northern Mariana Islands', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
    'PW': 'Palau', 'PA': 'Pennsylvania', 'PR': 'Puerto Rico', 'RI': 'Rhode Island',
    'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
    'UT': 'Utah', 'VT': 'Vermont', 'VI': 'Virgin Islands', 'VA': 'Virginia',
    'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}

USPS_BASE_URL = 'https://tools.usps.com/go/ZipLookupResultsAction!input.action'


def usps_request(**kwargs):

    print kwargs
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