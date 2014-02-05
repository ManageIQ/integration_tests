""" A model of a Cloud Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var amqp_form: A :py:class:`cfme.web_ui.Form` object describing the AMQP credentials form.
"""

from functools import partial
import ui_navigate as nav
import cfme
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.web_ui import Region, Quadicon, Form, fill
import cfme.web_ui.flash as flash
import cfme.fixtures.pytest_selenium as browser
import utils.conf as conf
from utils.update import Updateable
import cfme.web_ui.toolbar as tb
from utils.wait import wait_for
from utils.providers import provider_factory
from cfme.exceptions import HostStatsNotContains, ProviderHasNoProperty, ProviderHasNoKey


# Common locators
page_specific_locators = Region(
    locators={
        'cancel_button': "//img[@title='Cancel']",
        'creds_validate_btn': "//div[@id='default_validate_buttons_on']"
                              "/ul[@id='form_buttons']/li/a/img",
        'creds_verify_disabled_btn': "//div[@id='default_validate_buttons_off']"
                                     "/ul[@id='form_buttons']/li/a/img",
    }
)

# Page specific locators
add_page = Region(
    locators={
        'add_submit': "//img[@alt='Add this Cloud Provider']",
    },
    title='CloudForms Management Engine: Cloud Providers')

edit_page = Region(
    locators={
        'save_button': "//img[@title='Save Changes']",
    })

details_page = Region(infoblock_type='detail')

# Forms
discover_form = Form(
    fields=[
        ('username', "//*[@id='userid']"),
        ('password', "//*[@id='password']"),
        ('password_verify', "//*[@id='verify']"),
        ('start_button', "//input[@name='start']"),
        ('cancel_button', "//input[@name='cancel']"),
    ])

properties_form = Form(
    fields=[
        ('type_select', "//*[@id='server_emstype']"),
        ('name_text', browser.ObservedText("//*[@id='name']")),
        ('hostname_text', "//*[@id='hostname']"),
        ('ipaddress_text', "//*[@id='ipaddress']"),
        ('amazon_region_select', "//*[@id='hostname']"),
        ('api_port', "//*[@id='port']"),
    ])

def_form = Form(
    fields=[
        ('button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('principal', browser.ObservedText("//*[@id='default_userid']")),
        ('secret', browser.ObservedText("//*[@id='default_password']")),
        ('verify_secret', browser.ObservedText("//*[@id='default_verify']")),
        ('validate_btn', page_specific_locators.creds_validate_btn)
    ])

amqp_form = Form(
    fields=[
        ('button', "//div[@id='auth_tabs']/ul/li/a[@href='#amqp']"),
        ('principal', browser.ObservedText("//*[@id='amqp_userid']")),
        ('secret', browser.ObservedText("//*[@id='amqp_password']")),
        ('verify_secret', browser.ObservedText("//*[@id='amqp_verify']")),
        ('validate_btn', page_specific_locators.creds_validate_btn)
    ])

cfg_btn = partial(tb.select, 'Configuration')

nav.add_branch('clouds_providers',
               {'cloud_provider_new': lambda: cfg_btn('Add a New Cloud Provider'),
                'cloud_provider_discover': lambda: cfg_btn('Discover Cloud Providers'),
                'cloud_provider': [lambda ctx: browser.click(Quadicon(ctx['provider'].name,
                                                                      'cloud_prov')),
                                   {'cloud_provider_edit':
                                    lambda: cfg_btn('Edit this Cloud Provider')}]})


class Provider(Updateable):
    """
    Abstract model of a cloud provider in cfme. See EC2Provider or OpenStackProvider.

    Args:
        name: Name of the provider.
        details: a details record (see EC2Details, OpenStackDetails inner class).
        credentials (Credential): see Credential inner class.
        key: The CFME key of the provider in the yaml.

    Usage:

        myprov = EC2Provider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """

    def __init__(self, name=None, credentials=None, zone=None, key=None):
        self.name = name
        self.credentials = credentials
        self.zone = zone
        self.key = key

    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using amqp type credential, amqp = True"""

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')

    def _submit(self, cancel, submit_button):
        if cancel:
            browser.click(page_specific_locators.cancel_button)
            # browser.wait_for_element(page.configuration_btn)
        else:
            browser.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, validate_credentials=False):
        """
        Creates a provider in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
               after all the information present in the Provider has been filled in the UI.
           validate_credentials (boolean): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        nav.go_to('cloud_provider_new')
        fill(properties_form, self._form_mapping(True, **self.__dict__))
        fill(self.credentials, validate=validate_credentials)
        self._submit(cancel, add_page.add_submit)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        nav.go_to('cloud_provider_edit', context={'provider': self})
        fill(properties_form, self._form_mapping(**updates))
        fill(self.credentials, validate=validate_credentials)
        self._submit(cancel, edit_page.save_button)

    def validate(self):
        """ Validates that the detail page matches the Providers information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. The details page is then refreshed
        continuously until the matching of all items is complete. A error will be raised
        if the match is not complete within a certain defined time period.
        """
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
        """ Returns the mgmt_system using the :py:func:`utils.providers.provider_factory` method.
        """
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')
        else:
            return provider_factory(self.key)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        if not self._on_detail_page():
            nav.go_to('cloud_provider', context={'provider': self})
        return details_page.infoblock.text(*ident)

    def _do_stats_match(self, host_stats, stats_to_match=None):
        """ A private function to match a set of statistics, with a Provider.

        This function checks if the list of stats match, if not, the page is refreshed.

        Note: Provider mgmt_system uses the same key names as this Provider class to avoid
            having to map keyname/attributes e.g. ``num_template``, ``num_vm``.

        Args:
            host_stats: A dict of host statistics as obtained from the mgmt_system.
            stats_to_match: A list of key/attribute names to match.

        Raises:
            KeyError: If the host stats does not contain the specified key.
            ProviderHasNoProperty: If the provider does not have the property defined.
        """
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
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        return browser.is_displayed('//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s")]'
                                    % self.name)

    @property
    def num_template(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        return int(self.get_detail("Relationships", "Images"))

    @property
    def num_vm(self):
        """ Returns the providers number of instances, as shown on the Details page."""
        return int(self.get_detail("Relationships", "Instances"))


class EC2Provider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None):
        super(EC2Provider, self).__init__(name=name, credentials=credentials,
                                          zone=zone, key=key)
        self.region = region

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Amazon EC2',
                'amazon_region_select': (browser.VALUE, kwargs.get('region'))}


class OpenStackProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None):
        super(OpenStackProvider, self).__init__(name=name, credentials=credentials,
                                                zone=zone, key=key)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenStack',
                'hostname_text': kwargs.get('hostname'),
                'api_port': kwargs.get('api_port'),
                'ipaddress_text': kwargs.get('ip_address')}


@fill.register(Provider.Credential)
def _sd_fill_credential(cred, validate=None):
    """How to fill in a credential (either amqp or default).  Validates the
    credential if that option is passed in.
    """
    mapping = {'principal': cred.principal,
               'secret': cred.secret,
               'verify_secret': cred.verify_secret,
               'validate_btn': validate}
    if cred.amqp:
        fill(amqp_form, mapping)
    else:
        fill(def_form, mapping)
    if validate:
        flash.assert_no_errors()


def get_credentials_from_config(credential_config_name):
    creds = conf.credentials[credential_config_name]
    return Provider.Credential(principal=creds['username'],
                               secret=creds['password'])


def get_from_config(provider_config_name):
    """
    Creates a Provider object given a yaml entry in cfme_data.

    Usage:
        get_from_config('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """

    prov_config = conf.cfme_data['management_systems'][provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    if prov_config.get('type') == 'ec2':
        return EC2Provider(name=prov_config['name'],
                           region=prov_config['region'],
                           credentials=credentials,
                           zone=prov_config['server_zone'],
                           key=provider_config_name)
    else:
        return OpenStackProvider(name=prov_config['name'],
                                 hostname=prov_config['hostname'],
                                 ip_address=prov_config['ipaddress'],
                                 api_port=prov_config['port'],
                                 credentials=credentials,
                                 zone=prov_config['server_zone'],
                                 key=provider_config_name)


def discover(credential, cancel=False):
    """
    Discover cloud providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
      credential (cfme.Credential):  Amazon discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
    """
    nav.go_to('cloud_provider_discover')
    if cancel:  # normalize so that the form filler only clicks either start or cancel
        cancel = True
    else:
        cancel = None
    form_data = {'start_button': not cancel,
                 'cancel_button': cancel}
    if credential:
        form_data.update({'username': credential.principal,
                          'password': credential.secret,
                          'password_verify': credential.verify_secret})
    fill(discover_form, form_data)
