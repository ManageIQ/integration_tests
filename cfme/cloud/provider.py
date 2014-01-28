from functools import partial
from selenium.webdriver.common.by import By
import ui_navigate as nav
import cfme
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.web_ui import Region, Quadicon, Form, InfoBlock
import cfme.web_ui.flash as flash
import cfme.fixtures.pytest_selenium as browser
import utils.conf as conf
from utils.update import Updateable
import cfme.web_ui.toolbar as tb
from utils.wait import wait_for
from utils.providers import provider_factory
from cfme.exceptions import HostStatsNotContains, ProviderHasNoProperty, ProviderHasNoKey

page = Region(
    locators={
        'add_submit': "//img[@alt='Add this Cloud Provider']",
        'creds_validate_btn': "//div[@id='default_validate_buttons_on']"
                              "/ul[@id='form_buttons']/li/a/img",
        'creds_verify_disabled_btn': "//div[@id='default_validate_buttons_off']"
                                     "/ul[@id='form_buttons']/li/a/img",
        'cancel_button': "//img[@title='Cancel']",
        'save_button': "//img[@title='Save Changes']",
    },
    title='CloudForms Management Engine: Cloud Providers')

discover_page = Region(
    locators={
        'start_button': "//input[@name='start']",
        'cancel_button': "//input[@name='cancel']",
        'username': "//*[@id='userid']",
        'password': "//*[@id='password']",
        'password_verify': "//*[@id='verify']",
        'form_title': (By.CSS_SELECTOR, "div.dhtmlxInfoBarLabel-2"),
    },
    title='CloudForms Management Engine: Cloud Providers')

form = Form(
    fields=[
        ('type_select', "//*[@id='server_emstype']"),
        ('name_text', "//*[@id='name']"),
        ('hostname_text', "//*[@id='hostname']"),
        ('ipaddress_text', "//*[@id='ipaddress']"),
        ('amazon_region_select', "//*[@id='hostname']"),
        ('api_port', "//*[@id='port']"),
    ])

def_form = Form(
    fields=[
        ('button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('principal', "//*[@id='default_userid']"),
        ('secret', "//*[@id='default_password']"),
        ('verify_secret', "//*[@id='default_verify']"),
    ])

ampq_form = Form(
    fields=[
        ('button', "//div[@id='auth_tabs']/ul/li/a[@href='#amqp']"),
        ('principal', "//*[@id='amqp_userid']"),
        ('secret', "//*[@id='amqp_password']"),
        ('verify_secret', "//*[@id='amqp_verify']")
    ])

cfg_btn = partial(tb.select, 'Configuration')
nav.add_branch('clouds_providers', {
    'cloud_provider_new': lambda: cfg_btn('Add a New Cloud Provider'),
    'cloud_provider_discover': lambda: cfg_btn('Discover Cloud Providers'),
    'cloud_provider': [lambda ctx: browser.click(Quadicon(ctx['provider'].name, "cloud_prov")), {
        'cloud_provider_edit': lambda: cfg_btn('Edit Selected Cloud Provider')}]
})

# setter(loc) = a function that when called with text
# sets textfield at loc to text.
setter = partial(partial, browser.set_text)


class Provider(Updateable):
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

    def __init__(self, name=None, details=None, credentials=None, zone=None, key=None):
        self.name = name
        self.details = details
        self.credentials = credentials
        self.zone = zone
        self.key = key

    class EC2Details(Updateable):
        '''Models EC2 provider details '''

        def __init__(self, region=None):
            self.details = {'amazon_region_select': region,
                            'type_select': 'Amazon EC2'}

    class OpenStackDetails(Updateable):
        '''Models Openstack provider details '''

        def __init__(self, hostname=None, ip_address=None, api_port=None):
            self.details = {'hostname_text': hostname,
                            'ipaddress_text': ip_address,
                            'api_port': api_port,
                            'type_select': 'OpenStack'}

    class Credential(cfme.Credential, Updateable):
        '''Provider credentials

           Args:
             **kwargs: If using amqp type credential, amqp = True'''

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')

    def _fill_details(self, details, credentials, cancel, submit_button):
        details.details.update({'name_text': self.name})
        form.fill_fields(details.details)
        if credentials.amqp:
            ampq_form.fill_fields(credentials.details)
        else:
            def_form.fill_fields(credentials.details)

        if cancel:
            browser.click(page.cancel_button)
            # browser.wait_for_element(page.configuration_btn)
        else:
            browser.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False):
        '''
        Creates a provider in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
              after all the information present in the Provider has been filled in the UI.
        '''

        nav.go_to('cloud_provider_new')
        self._fill_details(self.details, self.credentials, cancel, page.add_submit)

    def update(self, updates, cancel=False):
        '''
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing
           cancel (boolean): whether to cancel out of the update.
        '''
        print(updates)

        nav.go_to('cloud_provider_edit', context={'provider': self})

        browser.set_text(page.name_text, updates.get('name'))

        # workaround - without this the save button doesn't enable
        browser.browser().execute_script('miqButtons("show")')

        self._fill_details(updates.get('details'),
                           updates.get('credentials'),
                           cancel, page.save_button)

    def validate(self):
        if not self._on_detail_page():
            nav.go_to('cloud_provider', context={'provider': self})

        stats_to_match = ['num_template', 'num_vm']

        client = self.get_mgmt_system()
        host_stats = client.stats(*stats_to_match)
        client.disconnect()

        ec, tc = wait_for(self._do_stats_match,
                          [host_stats, stats_to_match],
                          message="do_stats_match",
                          num_sec=300)

    def get_mgmt_system(self):
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')
        else:
            return provider_factory(self.key)

    def get_detail(self, *ident):
        if not self._on_detail_page():
            nav.go_to('cloud_provider', context={'provider': self})
        ib = InfoBlock("detail")
        return ib.text(*ident)

    def _do_stats_match(self, host_stats, stats_to_match=None):
        for stat in stats_to_match:
            try:
                if host_stats[stat] != getattr(self, stat):
                    browser.refresh()
                    return False
            except KeyError:
                raise HostStatsNotContains("Host stats information does not contain '%s'" % stat)
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '%s'" % stat)
        else:
            return True

    def _on_detail_page(self):
        return browser.is_displayed('//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s")]'
                                    % self.name)

    @property
    def num_template(self):
        return int(self.get_detail("Relationships", "Images"))

    @property
    def num_vm(self):
        return int(self.get_detail("Relationships", "Instances"))


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
                                      secret=creds['password'],
                                      verify_secret=creds['password'])
    if prov_config.get('type') == 'ec2':
        details = Provider.EC2Details(region=prov_config['region'])
    else:
        details = Provider.OpenStackDetails(hostname=prov_config['hostname'],
                                            ip_address=prov_config['ipaddress'],
                                            api_port=prov_config['port'])
    return Provider(name=prov_config['name'],
                    details=details,
                    credentials=credentials,
                    zone=prov_config['server_zone'],
                    key=provider_config_name)


def discover(credential, cancel=False):
    '''
    Discover cloud providers.

    Args:
      credential (cfme.Credential):  Amazon discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
    '''

    nav.go_to('cloud_provider_discover')
    if credential:
        credential.fill(setter(discover_page.username),
                        setter(discover_page.password),
                        setter(discover_page.password_verify))
    if cancel:
        browser.click(discover_page.cancel_button)
    else:
        browser.click(discover_page.start_button)
