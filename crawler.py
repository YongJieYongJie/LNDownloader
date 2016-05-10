import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl
from bs4 import BeautifulSoup
import pickle
import random
import datetime
import time
import getpass

# program configuration constants
TRUNCATE_LENGTH = 80
REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en-US;q=0.8,en;q=0.6',
        'Upgrade-Insecure-Requests': '1'
        }
INVALID_FILENAME_CHARS = '\/:*?"<>|'

# NUS and LawNet related constants
LOGIN_URL = 'https://proxylogin.nus.edu.sg/lawproxy1/public/login_form.asp?logup=false&url=http://www.lawnet.sg/lawnet/ip-access'
POST_URL_FOR_SEARCH = 'https://www-lawnet-sg.lawproxy1.nus.edu.sg/lawnet/group/lawnet/result-page'
LOGOUT_URL = 'https://www-lawnet-sg.lawproxy1.nus.edu.sg/lawnet/c/portal/logout?referer=/lawnet/web/lawnet/home'
SPECIFIED_RESOURCES = [1,2] # 1 = 'Judgments', 2 = 'Singapore Law Reports'

# Based urls, to be interpolated with user input / non-deterministic strings from server
BASE_ACCEPT_BUTTON_POST_URL = 'https://lawproxy1.nus.edu.sg/login?user=nusstu-{}&ticket={}%24gCASETRACK%2BHEINONLINE%2BLAWNET%2BWESTLAW%24e&qurl=http%3A%2F%2Fwww%2Elawnet%2Esg%2Flawnet%2Fip%2Daccess'
BASE_PAGE_N_URL = 'https://www-lawnet-sg.lawproxy1.nus.edu.sg/lawnet/group/lawnet/result-page?p_p_id=legalresearchresultpage_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_selectedSortFilter=relevance&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_isParentFilterSelected=false&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_isGrandParentFilterSelected=false&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_action=actionPageNo&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_searchId={}&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_enteredkeywordNumber=10&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_cur={}&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_pre=0'
BASE_DOCUMENT_URL = 'https://www-lawnet-sg.lawproxy1.nus.edu.sg/lawnet/group/lawnet/page-content?p_p_id=legalresearchpagecontent_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchpagecontent_WAR_lawnet3legalresearchportlet_action=openContentPage&contentDocID={}'


# needed to ensure TLSv1 is used
class TLSv1Adapter(HTTPAdapter):


    def init_poolmanager(self, connections, maxsize, block=False):

        self.poolmanager = PoolManager(num_pools=connections,
                maxsize=maxsize,
                block=block,
                ssl_version=ssl.PROTOCOL_TLSv1)


class Altlawdownloader():


    random.seed(datetime.datetime.now())
    session = requests.Session()
    session.mount('https://', TLSv1Adapter()) # this is to make the session use the TLSv1 certificate

    # main
    def serve_some_justice(self):

        username, password = self.prompt_for_login_credentials()
        search_term = self.prompt_for_search_term()

        self.log('[<==] Logging in to NUS Proxy')
        response_from_proxy_login = self.log_in_to_nus_proxy(username, password)
        self.log('[*] Reached holding page with "I Accept" button')

        self.log('[<==] Clicking "I Accept" button')
        response_from_i_accept = self.click_i_accept_button(response_from_proxy_login, username)
        self.log('[*] You are now logged in to LawNet')

        # try block needed to ensure user is logged out in case of exceptions
        try:
            self.log('[<==] Sending search request for search term "{}"'.format(search_term))
            response_from_search_request = self.send_search_request(response_from_i_accept, search_term)
            self.log('[*] Processing search results')

            search_id, num_search_results, num_result_pages = self.pre_process_for_crawling(response_from_search_request)
            self.log('[*] Search term "{}" returned {} results on {} page(s)'.format(search_term, num_search_results, num_result_pages))

            self.log('[*] Let the crawling begin')
            self.start_crawling(search_id, num_result_pages)

        finally:
            self.log('[<==] Logging out of LawNet')
            self.log_out()

    def prompt_for_login_credentials(self):

        username = raw_input('Username here: ')
        password = getpass.getpass('Password here: ')
        return username, password

    def prompt_for_search_term(self):

        search_term = raw_input('What do you want to search for? ')
        return search_term

    def log_in_to_nus_proxy(self, username, password):

        login_params = {'domain': 'NUSSTU', 'user': username, 'pass': password}
        response = self.session.post(LOGIN_URL, data=login_params, headers=REQUEST_HEADERS)
        self.sleepabit()
        return response

    def click_i_accept_button(self, response_from_proxy_login, username):

        security_ticket = self.get_security_ticket(response_from_proxy_login)
        accept_button_post_url = BASE_ACCEPT_BUTTON_POST_URL.format(username, security_ticket)
        accept_button_post_data = 'I Accept'
        response = self.session.post(accept_button_post_url, data=accept_button_post_data, headers=REQUEST_HEADERS)
        self.sleepabit()

        return response

    def send_search_request(self, response_from_i_accept, search_term):

        hidden_form_value = self.get_hidden_form_value(response_from_i_accept)
        search_params = {
                'basicSearchKey': search_term,
                '_searchbasicformportlet_WAR_lawnet3legalresearchportlet_formDate': hidden_form_value,
                'p_p_id': 'legalresearchresultpage_WAR_lawnet3legalresearchportlet',
                'p_p_lifecycle': 1,
                'p_p_state': 'normal',
                'p_p_mode': 'view',
                'p_p_col_id': 'column2',
                'p_p_col_count': 1,
                '_legalresearchresultpage_WAR_lawnet3legalresearchportlet_action': 'basicSeachActionURL',
                '_legalresearchresultpage_WAR_lawnet3legalresearchportlet_searchType': 0,
                'category': SPECIFIED_RESOURCES
                }
        response = self.session.post(POST_URL_FOR_SEARCH, data=search_params, headers=REQUEST_HEADERS)
        self.sleepabit()
        return response

    def pre_process_for_crawling(self, response_from_search_request):

        search_id = self.get_search_id(response_from_search_request)
        num_search_results = self.get_num_search_results(response_from_search_request)
        num_result_pages = self.get_num_results_pages(num_search_results)
        return search_id, num_search_results, num_result_pages

    def start_crawling(self, search_id, num_result_pages):

        result_page_urls = self.get_result_page_urls(search_id, num_result_pages)
        current_page_number = 1

        for result_page_url in result_page_urls:
            self.log('[*] Crawling page {} of {}'.format(current_page_number, num_result_pages))
            document_urls = self.get_document_urls_for_single_page(result_page_url)
            self.sleepabit()

            for document_url in document_urls:
                self.save_document(document_url)

            current_page_number += 1

    def log_out(self):

        self.sleepabit()
        response = self.session.get(LOGOUT_URL, headers = REQUEST_HEADERS)
        self.log('[*] You are logged out of LawNet')

    def save_document(self, document_url):

        response = self.session.get(document_url, headers=REQUEST_HEADERS)
        parsed_document_page = BeautifulSoup(response.content, 'html.parser')

        case_name = self.get_case_name(parsed_document_page)
        citation = self.get_citation(parsed_document_page)
        case_name_with_citation = u'{}, {}'.format(case_name, citation)
        self.log(u'[==>] Saving case: {}'.format(case_name_with_citation))

        sanitized_case_name = self.get_sanitized_case_name(case_name_with_citation)
        self.save_object(response.content, u'{}.html'.format(sanitized_case_name))

        self.sleepabit() # Absolutely needed

    def save_last_seen_page(self, response):

        self.save_object(response.content, 'last_seen_page.html')

    def save_object(self, obj, filename):

        with open(filename, 'wb') as output:
            pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)
        output.close

    def get_security_ticket(self, response_from_proxy_login):

        i_accept_page_url = response_from_proxy_login.url
        security_ticket = ((i_accept_page_url.split('ticket%3D')[1]).split('%2524gCASETRACK'))[0]
        security_ticket = security_ticket.replace('%2524', '%24') # because of the percentage sign being encoded as %25

        return security_ticket

    def get_hidden_form_value(self, response_from_i_accept):

        parsed_search_page = BeautifulSoup(response_from_i_accept.content, 'html.parser')
        return (parsed_search_page.find('input', {'name': '_searchbasicformportlet_WAR_lawnet3legalresearchportlet_formDate'}))['value']

    def get_search_id(self, response_from_search_request):

        return (response_from_search_request.url).split('legalresearchresultpage_WAR_lawnet3legalresearchportlet_searchId=')[1]

    def get_num_search_results(self, response_from_search_request):

        parsed_results_page = BeautifulSoup(response_from_search_request.content, 'html.parser')
        return int(parsed_results_page.find('span', {'class': 'search-result-no'}).get_text())

    def get_num_results_pages(self, num_search_results):

        RESULTS_PER_PAGE = 10

        # simple implemenation of ceiling function; didn't want to import math just for this
        num_result_pages = num_search_results / RESULTS_PER_PAGE
        if (num_search_results % RESULTS_PER_PAGE != 0):
            num_result_pages += 1

        return num_result_pages

    def get_result_page_urls(self, search_id, last_page_number):

        result_page_urls = []
        for i in range(1, last_page_number + 1):
            result_page_urls.append(self.get_url_of_page_n(search_id, i))
        return result_page_urls

    def get_url_of_page_n(self, search_id, current_page_number):

        page_n_url = BASE_PAGE_N_URL.format(search_id, current_page_number)
        return page_n_url

    def get_document_urls_for_single_page(self, result_page_url):

        response = self.session.get(result_page_url, headers=REQUEST_HEADERS)
        parsed_results_page = BeautifulSoup(response.content, 'html.parser')

        document_urls = []

        for html_tag in parsed_results_page.findAll('a', {'class': 'document-title'}):
            document_url = self.get_document_url_from_html_tag(html_tag)
            document_urls.append(document_url)

        return document_urls

    def get_document_url_from_html_tag(self, html_tag):

        document_id = html_tag['onclick'].split("viewPageContent('")[1].replace("')", '')
        document_id = document_id.replace(' ', '%20') #this yields contentDocID
        document_url = BASE_DOCUMENT_URL.format(document_id)

        return document_url

    def get_case_name(self, parsed_document_page):

        return parsed_document_page.find('span', class_ = 'caseTitle').get_text().strip()

    def get_citation(self, parsed_document_page):

        if parsed_document_page.find('span', class_ = 'Citation offhyperlink'):
            return parsed_document_page.find('span', class_ = 'Citation offhyperlink').get_text().strip()
        else:
            return ''

    def get_sanitized_case_name(self, case_name_with_citation):

        for char in INVALID_FILENAME_CHARS:
            case_name_with_citation.replace(char, '')

        return case_name_with_citation

    def sleepabit(self):

        time.sleep(random.uniform(2,8))

    def track_redirection(self, response):

        if self.is_redirected(response):
            self.log('[*] Followed redirections through the following:')
            for intermediate_response in response.history:
                self.log_http_response(intermediate_response)

        self.log('[*] Received http response:')
        self.log_http_response(response)
        self.log('[*] Cookies are set to:')
        self.log_cookies(response.cookies.get_dict())

    def is_redirected(self, response):

        return response.history

    def log(self, message, truncate=True):

        if truncate and len(message) > TRUNCATE_LENGTH-3:
            print u'{}...'.format(message[:TRUNCATE_LENGTH-3])
        else:
            print message

    def log_http_response(self, response):

        self.log('::{} {}:: {}'.format(response.status_code, response.reason, response.url), False)

    def log_http_request(self, request):

        self.log('[<==] Sending http request to:\n{}'.format(request), False)

    def log_cookies(self, cookies):

        self.log(cookies, False)


app = Altlawdownloader()
app.serve_some_justice()
