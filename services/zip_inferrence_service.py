import requests
import re
# disable invalid SSL warnings - doesn't matter
requests.packages.urllib3.disable_warnings()

USPS_BASE_URL = 'https://tools.usps.com/go/ZipLookupResultsAction!input.action'

def usps_zip_lookup(street_address, city, state, zip=''):
    """
    Use usps to look up zip5 and zip4
    @param street_address: [String] street address
    @param city: [String] city name
    @param state: [String] state name
    @return: [Tuple] (<(String\d{5}|None)>,<(String\d{4}|None)>)
    """

    # construct get parameters string
    get_params = "resultMode=0&companyName=&address1={addr1}&address2=&city={city}&state={state}&urbanCode=&postalCode=&zip={zip}".format(addr1=street_address, city=city, state=state, zip=zip)

    # make request. need to spoof headers or get infinite redirect
    r = requests.get(USPS_BASE_URL + '?' + get_params, verify=False,
                     headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.99 Safari/537.36'})

    # retrieve raw html
    html = r.text

    # try to extract zip5 and zip4 from HTML. Return None if can't be resolved.
    try: zip5 = re.sub("""<("[^"]*"|'[^']*'|[^'">])*>""",'',(re.search('<span class=\"zip\".*>\d{5}\<\/span\>', html)).group(0))
    except: zip5 = None
    try: zip4 = re.sub("""<("[^"]*"|'[^']*'|[^'">])*>""",'',(re.search('<span class=\"zip4\">\d{4}\<\/span\>', html)).group(0))
    except: zip4 = None

    return (zip5, zip4)