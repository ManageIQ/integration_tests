from selenium.webdriver.common.by import By
from cfme.web_ui import Region
import cfme.fixtures.pytest_selenium as browser
import ui_navigate as nav
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.web_ui import Quadicon
import cfme
from functools import partial
import utils.conf as conf
from copy import copy

page = Region(locators=
              {'configuration_button': (By.CSS_SELECTOR,
                                        "div.dhx_toolbar_btn[title='Configuration']"),
               'discover_button': (By.CSS_SELECTOR,
                                   "tr[title='Discover Cloud Providers']>td.td_btn_txt>"
                                   "div.btn_sel_text"),
               'edit_button': (By.CSS_SELECTOR,
                               "tr[title='Select a single Cloud Provider to edit']>"
                               "td.td_btn_txt>div.btn_sel_text"),
               'remove_button': (By.CSS_SELECTOR,
                                 "tr[title='Remove selected Cloud Providers from the VMDB']>"
                                 "td.td_btn_txt>div.btn_sel_text"),
               'add_button': (By.CSS_SELECTOR, "tr[title='Add a New Cloud Provider']>"
                              "td.td_btn_txt>div.btn_sel_text"),
               'add_submit': (By.CSS_SELECTOR, "img[alt='Add this Cloud Provider']"),
               'credentials_validate_button': (By.CSS_SELECTOR, "div#default_validate_buttons_on >"
                                             " ul#form_buttons > li > a > img"),
               'credentials_verify_disabled_button': (By.CSS_SELECTOR,
                                                      "div#default_validate_buttons_off > "
                                                      "ul#form_buttons > li > a > img"),
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
               'default_credentials_button': (By.CSS_SELECTOR,
                                              "div#auth_tabs > ul > li > a[href='#default']"),
               'amqp_credentials_button': (By.CSS_SELECTOR,
                                           "div#auth_tabs > ul > li > a[href='#amqp']"),
               'api_port': (By.ID, "port")},
              title='CloudForms Management Engine: Cloud Providers')


discover_page = Region(locators=
                       {'start_button': (By.CSS_SELECTOR, "input[name='start']"),
                        'cancel_button': (By.CSS_SELECTOR, "input[name='cancel']"),
                        'username': (By.ID, 'userid'),
                        'password': (By.ID, 'password'),
                        'password_verify': (By.ID, 'verify'),
                        'form_title': (By.CSS_SELECTOR, "div.dhtmlxInfoBarLabel-2")},
                       title='CloudForms Management Engine: Cloud Providers')

nav.add_branch('clouds_providers',
               {'clouds_providers_new': browser.click_fn(page.configuration_button,
                                                         page.add_button),
                'clouds_providers_discover': browser.click_fn(page.configuration_button,
                                                              page.discover_button),
                'clouds_provider': lambda ctx: browser.click(Quadicon(ctx['provider'].name))})

# setter(loc) = a function that when called with text
# sets textfield at loc to text.
setter = partial(partial, browser.set_text)


class Provider(object):
    '''
    Models a cloud provider in cfme

    Args:
        name: Name of the provider
        details: a details record (see EC2Details, OpenStackDetails inner class)
        credentials (Credential): see Credential inner class

    Usage:

        myprov = Provider(name='foo',
                          details=Provider.EC2Details(region='US West (Oregon)'),
                          credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    '''

    def __init__(self, name=None, details=None, credentials=None, zone=None):
        self.name = name
        self.details = details
        self.credentials = credentials
        self.zone = zone

    class EC2Details(object):
        '''Models EC2 provider details '''
        select_text = 'Amazon EC2'

        def __init__(self, region=None):
            self.region = region

    class OpenStackDetails(object):
        '''Models Openstack provider details '''
        select_text = 'OpenStack'

        def __init__(self, hostname=None, ip_address=None, api_port=None):
            self.hostname = hostname
            self.ip_address = ip_address
            self.api_port = api_port

    class Credential(cfme.Credential):
        '''Provider credentials

           Args:
             **kwargs: If using amqp type credential, amqp = True'''

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')

    def create(self, cancel=False):
        '''
        Creates a provider in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
              after all the information present in the Provider has been filled in the UI.
        '''

        nav.go_to('clouds_providers_new')
        browser.set_text(page.name_text, self.name)

        if self.details:
            details = self.details
            browser.select_by_text(page.type_select, details.select_text)
            if type(details) == self.EC2Details:
                browser.select_by_value(page.amazon_region_select, details.region)
            elif type(details) == self.OpenStackDetails:
                browser.set_text(page.hostname_text, details.hostname)
                browser.set_text(page.ipaddress_text, details.ip_address)
                browser.set_text(page.hostname_text, details.hostname)
            else:
                raise TypeError("Unknown type of provider details: %s" % type(details))

        if self.credentials:
            if self.credentials.amqp:
                browser.click(page.amqp_credentials_button)
                self.credentials.fill(setter(page.amqp_userid_text),
                                      setter(page.amqp_password_text),
                                      setter(page.amqp_verify_text))
            else:
                self.credentials.fill(setter(page.userid_text),
                                      setter(page.password_text),
                                      setter(page.verify_password_text))
        if cancel:
            browser.click(page.cancel_button)
            # browser.wait_for_element(page.configuration_button)
        else:
            browser.click(page.add_submit)

    def update(self, f):
        pass
        # need to figure out a way to leave object unchanged if update
        # fails, or maybe just don't use mutable objects at all to
        # represent the Provider's state in CFME?  (in other words,
        # we could just return a new "immutable" object each time?


def get_from_config(provider_config_name):
    '''
    Creates a Provider object given a yaml entry in cfme_data.

    Usage:
    get_from_config('ec2east')

    Returns:
    A Provider object that has methods that operate on CFME
    '''

    prov_config = conf.cfme_data['management_systems'][provider_config_name]
    creds = conf.credentials[prov_config['credentials']]
    credentials = Provider.Credential(principal=creds['username'],
                                      secret=creds['password'])
    if prov_config['region']:
        details = Provider.EC2Details(region=prov_config['region'])
    else:
        details = Provider.OpenStackDetails(hostname=prov_config['hostname'],
                                            ip_address=prov_config['ipaddress'],
                                            api_port=prov_config['port'])
    return Provider(name=prov_config['name'],
                    details=details,
                    credentials=credentials,
                    zone=prov_config['server_zone'])


def discover(credential, cancel=False):
    '''
    Discover cloud providers.

    Args:
      credential (cfme.Credential):  Amazon discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
    '''

    nav.go_to('clouds_providers_discover')
    if credential:
        credential.fill(setter(discover_page.username),
                        setter(discover_page.password),
                        setter(discover_page.password_verify))
    if cancel:
        browser.click(discover_page.cancel_button)
    else:
        browser.click(discover_page.start_button)
