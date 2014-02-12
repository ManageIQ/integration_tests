""" A model of an Infrastructure Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var candu_form: A :py:class:`cfme.web_ui.Form` object describing the C&U credentials form.
"""

from functools import partial

import ui_navigate as nav

import cfme
import cfme.fixtures.pytest_selenium as browser
import cfme.web_ui.flash as flash
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
import cfme.web_ui.toolbar as tb
import utils.conf as conf
from cfme.exceptions import HostStatsNotContains, ProviderHasNoProperty, ProviderHasNoKey
from cfme.web_ui import Region, Quadicon, Form, fill
from utils.providers import provider_factory, list_infra_providers
from utils.update import Updateable
from utils.wait import wait_for


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
        'add_submit': "//img[@alt='Add this Infrastructure Provider']",
    },
    title='CloudForms Management Engine: Infrastructure Providers')

edit_page = Region(
    locators={
        'save_button': "//img[@title='Save Changes']",
    })

details_page = Region(infoblock_type='detail')

# Forms
discover_form = Form(
    fields=[
        ('rhevm_chk', "//input[@id='discover_type_rhevm']"),
        ('vmware_chk', "//input[@id='discover_type_virtualcenter']"),
        ('from_0', "//*[@id='from_first']"),
        ('from_1', "//*[@id='from_second']"),
        ('from_2', "//*[@id='from_third']"),
        ('from_3', "//*[@id='from_fourth']"),
        ('to_3', "//*[@id='to_fourth']"),
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

candu_form = Form(
    fields=[
        ('button', "//div[@id='auth_tabs']/ul/li/a[@href='#metrics']"),
        ('principal', browser.ObservedText("//*[@id='metrics_userid']")),
        ('secret', browser.ObservedText("//*[@id='metrics_password']")),
        ('verify_secret', browser.ObservedText("//*[@id='metrics_verify']")),
        ('validate_btn', page_specific_locators.creds_validate_btn)
    ])

cfg_btn = partial(tb.select, 'Configuration')

nav.add_branch('infrastructure_providers',
               {'infrastructure_provider_new': lambda: cfg_btn('Add a New Infrastructure Provider'),
                'infrastructure_provider_discover': lambda: cfg_btn(
                    'Discover Infrastructure Providers'),
                'infrastructure_provider': [lambda ctx: browser.click(Quadicon(ctx['provider'].name,
                                                                      'infra_prov')),
                                   {'infrastructure_provider_edit':
                                    lambda: cfg_btn('Edit this Infrastructure Provider')}]})


class Provider(Updateable):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.

    Args:
        name: Name of the provider.
        details: a details record (see VMwareDetails, RHEVMDetails inner class).
        credentials (Credential): see Credential inner class.
        key: The CFME key of the provider in the yaml.

    Usage:

        myprov = VMwareProvider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """

    def __init__(self, name=None, credentials=None, key=None, zone=None):
        self.name = name
        self.credentials = credentials
        self.key = key
        self.zone = zone

    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using C & U database type credential, candu = True"""

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.candu = kwargs.get('candu')

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
        browser.force_navigate('infrastructure_provider_new')
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

        nav.go_to('infrastructure_provider_edit', context={'provider': self})
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
            nav.go_to('infrastructure_provider', context={'provider': self})

        stats_to_match = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']

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
            nav.go_to('infrastructure_provider', context={'provider': self})
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
        return int(self.get_detail("Relationships", "Templates"))

    @property
    def num_vm(self):
        """ Returns the providers number of instances, as shown on the Details page."""
        return int(self.get_detail("Relationships", "VMs"))

    @property
    def num_datastore(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        return int(self.get_detail("Relationships", "Datastores"))

    @property
    def num_host(self):
        """ Returns the providers number of instances, as shown on the Details page."""
        return int(self.get_detail("Relationships", "Hosts"))

    @property
    def num_cluster(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        return int(self.get_detail("Relationships", "Clusters"))


class VMwareProvider(Provider):
    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None):
        super(VMwareProvider, self).__init__(name=name, credentials=credentials,
                                             zone=zone, key=key)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'VMware vCenter',
                'hostname_text': kwargs.get('hostname'),
                'ipaddress_text': kwargs.get('ip_address')}


class RHEVMProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, start_ip=None, end_ip=None):
        super(RHEVMProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key)

        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.start_ip = start_ip
        self.end_ip = end_ip

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Red Hat Enterprise Virtualization Manager',
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
    if cred.candu:
        fill(candu_form, mapping)
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
        get_from_config('rhevm32')

    Returns: A Provider object that has methods that operate on CFME
    """

    prov_config = conf.cfme_data['management_systems'][provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    if prov_config.get('type') == 'virtualcenter':
        return VMwareProvider(name=prov_config['name'],
                              hostname=prov_config['hostname'],
                              ip_address=prov_config['ipaddress'],
                              credentials=credentials,
                              zone=prov_config['server_zone'],
                              key=provider_config_name,
                              start_ip=prov_config['discovery_range']['start'],
                              end_ip=prov_config['discovery_range']['end'])
    else:
        return RHEVMProvider(name=prov_config['name'],
                             hostname=prov_config['hostname'],
                             ip_address=prov_config['ipaddress'],
                             api_port='',
                             credentials=credentials,
                             zone=prov_config['server_zone'],
                             key=provider_config_name,
                             start_ip=prov_config['discovery_range']['start'],
                             end_ip=prov_config['discovery_range']['end'])


def discover_from_provider(provider_data):
    """
    Begins provider discovery from a provider instance

    Usage:
        discover_from_config(provider.get_from_config('rhevm'))
    """
    vmware = True if isinstance(provider_data, VMwareProvider) else False
    rhevm = True if isinstance(provider_data, RHEVMProvider) else False
    discover(rhevm, vmware, cancel=False, start_ip=provider_data.start_ip,
             end_ip=provider_data.end_ip)


def discover(rhevm=False, vmware=False, cancel=False, start_ip=None, end_ip=None):
    """
    Discover infrastructure providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
        rhvem: Whether to scan for RHEVM providers
        vmware: Whether to scan for VMware providers
        cancel:  Whether to cancel out of the discover UI.
    """
    browser.force_navigate('infrastructure_provider_discover')
    if cancel:  # normalize so that the form filler only clicks either start or cancel
        cancel = True
    else:
        cancel = None
    form_data = {'start_button': not cancel,
                 'cancel_button': cancel}
    if rhevm:
        form_data.update({'rhevm_chk': True})
    if vmware:
        form_data.update({'vmware_chk': True})

    if start_ip:
        for idx, octet in enumerate(start_ip.split('.')):
            key = 'from_%i' % idx
            form_data.update({key: octet})
    if end_ip:
        end_octet = end_ip.split('.')[-1]
        form_data.update({'to_3': end_octet})

    fill(discover_form, form_data)


def setup_provider(provider_name):
    provider = get_from_config(provider_name)
    provider.create(validate_credentials=True)


def setup_providers():
    for provider_name in list_infra_providers():
        setup_provider(provider_name)
