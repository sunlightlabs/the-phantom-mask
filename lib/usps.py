import re
import requests

requests.packages.urllib3.disable_warnings()

CODE_TO_STATE = {
    "WA": "WASHINGTON", "VA": "VIRGINIA", "DE": "DELAWARE",
    "DC": "DISTRICT OF COLUMBIA", "WI": "WISCONSIN", "WV": "WEST VIRGINIA",
    "HI": "HAWAII", "AE": "Armed Forces Middle East", "FL": "FLORIDA",
    "FM": "FEDERATED STATES OF MICRONESIA", "WY": "WYOMING",
    "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY", "NM": "NEW MEXICO",
    "TX": "TEXAS", "LA": "LOUISIANA", "NC": "NORTH CAROLINA",
    "ND": "NORTH DAKOTA", "NE": "NEBRASKA",
    "TN": "TENNESSEE", "NY": "NEW YORK", "PA": "PENNSYLVANIA",
    "CA": "CALIFORNIA", "NV": "NEVADA", "AA": "Armed Forces Americas",
    "PW": "PALAU", "GU": "GUAM", "CO": "COLORADO",
    "VI": "VIRGIN ISLANDS", "AK": "ALASKA",
    "AL": "ALABAMA", "AP": "Armed Forces Pacific",
    "AS": "AMERICAN SAMOA", "AR": "ARKANSAS",
    "VT": "VERMONT", "IL": "ILLINOIS",
    "GA": "GEORGIA", "IN": "INDIANA", "IA": "IOWA",
    "OK": "OKLAHOMA", "AZ": "ARIZONA", "ID": "IDAHO",
    "CT": "CONNECTICUT", "ME": "MAINE", "MD": "MARYLAND",
    "MA": "MASSACHUSETTS", "OH": "OHIO", "UT": "UTAH",
    "MO": "MISSOURI", "MN": "MINNESOTA", "MI": "MICHIGAN",
    "MH": "MARSHALL ISLANDS", "RI": "RHODE ISLAND",
    "KS": "KANSAS", "MT": "MONTANA", "MP": "NORTHERN MARIANA ISLANDS",
    "MS": "MISSISSIPPI", "PR": "PUERTO RICO",
    "SC": "SOUTH CAROLINA", "KY": "KENTUCKY", "OR": "OREGON",
    "SD": "SOUTH DAKOTA"
}

USPS_BASE_URL = 'https://tools.usps.com/go/ZipLookupResultsAction!input.action'

def usps_zip_lookup(street_address, city, state, zip=''):
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
        'zip': zip
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