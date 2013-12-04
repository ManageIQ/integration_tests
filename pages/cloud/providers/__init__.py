from selenium.webdriver.common.by import By
from pages.region import Region
import fixtures.pytest_selenium as browser
import fixtures.navigation as nav
import pages.regions.header_menu  # so that menu is already loaded before grafting onto it
import utils.credentials as cred

page = Region(locators=
              {'configuration_button': (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']"),
               'discover_button': (By.CSS_SELECTOR, "tr[title='Discover Cloud Providers']>td.td_btn_txt>div.btn_sel_text"),
               'edit_button': (By.CSS_SELECTOR, "tr[title='Select a single Cloud Provider to edit']>td.td_btn_txt>div.btn_sel_text"),
               'remove_button': (By.CSS_SELECTOR, "tr[title='Remove selected Cloud Providers from the VMDB']>td.td_btn_txt>div.btn_sel_text"),
               'add_button': (By.CSS_SELECTOR, "tr[title='Add a New Cloud Provider']>td.td_btn_txt>div.btn_sel_text"),
               'add_submit': (By.CSS_SELECTOR, "img[alt='Add this Cloud Provider']"),
               'credentials_verify_button': (By.CSS_SELECTOR, "div#default_validate_buttons_on > ul#form_buttons > li > a > img"),
               'credentials_verify_disabled_button': (By.CSS_SELECTOR, "div#default_validate_buttons_off > ul#form_buttons > li > a > img"),
               'cancel_button': (By.CSS_SELECTOR, "img[title='Cancel']"),
               'name_text': (By.ID, "name"),
               'hostname_text': (By.ID, "hostname"),
               'ipaddress_text': (By.ID, "ipaddress"),
               'type_select': (By.ID, "server_emstype"),
               'amazon_region_select': (By.ID, "hostname"),
               'userid_text': (By.ID, "default_userid"),
               'password_text': (By.ID, "default_password"),
               'verify_password_text': (By.ID, "default_verify"),
               'amqp_userid_text': (By.ID, "amqp_userid"),
               'amqp_password_text': (By.ID, "amqp_password"),
               'amqp_verify_text': (By.ID, "amqp_verify"),
               'server_zone_text': (By.ID, "server_zone"),
               'default_credentials_button': (By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#default']"),
               'amqp_credentials_button': (By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#amqp']"),
               'api_port': (By.ID, "port"),},
              title='CloudForms Management Engine: Cloud Providers')


nav.add_branch('clouds_providers',
               {'clouds_providers_new': nav.click_fn(page.configuration_button, page.add_button)})


class Provider(object):
    """Models a provider class in cfme
    """
    
    def __init__(self, name=None, details=None, credentials=None, zone=None):
        """
        
        Arguments:
        - `name`:
        - `prov_type`:
        - `details`:
        - `credentials`:
        """
        self.name = name
        self.details = details
        self.credentials = credentials
        self.zone = zone

    class EC2Details(object):
        """Models EC2 provider details
        """
        select_text = 'Amazon EC2'

        def __init__(self, region=None):
            """
            
            Arguments:
            - `region`:
            """
            self.region = region

    class OpenStackDetails(object):
        """Models Openstack provider details
        """
        select_text = 'OpenStack'

        def __init__(self, hostname=None, ip_address=None, api_port=None):
            """
            
            Arguments:
            - `hostname`:
            - `ip_address`:
            - `api_port`:
            """
            self.hostname = hostname
            self.ip_address = ip_address
            self.api_port = api_port

    class Credential(cred.Credential):
        '''If using amqp type credential, amqp = True'''

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')

    def create(self, cancel=False):
        nav.go_to('clouds_providers_new')
        browser.set_text(page.name_text, self.name)

        if self.details:
            details = self.details
            browser.select_by_text(page.type_select, details.select_text)
            if type(details) == self.EC2Details:
                browser.select_by_text(page.amazon_region_select, details.region)
            elif type(details) == self.OpenStackDetails:
                browser.set_text(page.hostname_text, details.hostname)
                browser.set_text(page.ipaddress_text, details.ip_address)
                browser.set_text(page.hostname_text, details.hostname)
            else:
                raise TypeError("Unknown type of provider details: %s" % type(details))

        if self.credentials:
            def setter(loc):
                return lambda text: browser.set_text(loc, text)

            if self.credentials.amqp:
                browser.click(page.amqp_credentials_button)
                self.credentials.fill(setter(page.amqp_userid_text),
                                      setter(page.amqp_password_text),
                                      setter(page.amqp_verify_text))
            else:
                self.credentials.fill(setter(page.userid_text),
                                      setter(page.password_text),
                                      setter(page.verify_password_text))
        browser.click(page.add_submit)

# How to use

# myprov = Provider(name='foo',
#                   details=Provider.EC2Details(region='US West (Oregon)'),
#                   credentials=Provider.Credential(principal='admin', secret='foobar'))
# myprov.create()
