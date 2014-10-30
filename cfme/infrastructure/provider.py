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
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
import cfme.web_ui.toolbar as tb
import utils.conf as conf
from cfme.exceptions import (
    HostStatsNotContains, ProviderHasNoProperty, ProviderHasNoKey, UnknownProviderType
)
from cfme.web_ui import Region, Quadicon, Form, Select, CheckboxTree, fill, form_buttons, paginator
from cfme.web_ui import Timelines
from cfme.web_ui.form_buttons import FormButton
from utils.log import logger
from utils.providers import provider_factory
from utils.update import Updateable
from utils.wait import wait_for, RefreshTimer
from utils import version
from utils.pretty import Pretty

add_infra_provider = FormButton("Add this Infrastructure Provider")

details_page = Region(infoblock_type='detail')

prov_timeline = Timelines('//div[@id="miq_timeline"]')

# Forms
discover_form = Form(
    fields=[
        ('rhevm_chk', "//input[@id='discover_type_rhevm']"),
        ('vmware_chk', "//input[@id='discover_type_virtualcenter']"),
        ('scvmm_chk', "//input[@id='discover_type_scvmm']"),
        ('from_0', "//*[@id='from_first']"),
        ('from_1', "//*[@id='from_second']"),
        ('from_2', "//*[@id='from_third']"),
        ('from_3', "//*[@id='from_fourth']"),
        ('to_3', "//*[@id='to_fourth']"),
        ('start_button', FormButton("Start the Host Discovery"))
    ])

properties_form = Form(
    fields=[
        ('type_select', Select("//*[@id='server_emstype']")),
        ('name_text', "//*[@id='name']"),
        ('hostname_text', "//*[@id='hostname']"),
        ('ipaddress_text', "//*[@id='ipaddress']"),
        ('api_port', "//*[@id='port']"),
        ('sec_protocol', Select("//*[@id='security_protocol']")),
        ('sec_realm', "//*[@id='realm']"),
    ])

credential_form = Form(
    fields=[
        ('default_button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('default_principal', "//*[@id='default_userid']"),
        ('default_secret', "//*[@id='default_password']"),
        ('default_verify_secret', "//*[@id='default_verify']"),
        ('candu_button', "//div[@id='auth_tabs']/ul/li/a[@href='#metrics']"),
        ('candu_principal', "//*[@id='metrics_userid']"),
        ('candu_secret', "//*[@id='metrics_password']"),
        ('candu_verify_secret', "//*[@id='metrics_verify']"),
        ('validate_btn', form_buttons.validate)
    ])

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')

nav.add_branch('infrastructure_providers',
               {'infrastructure_provider_new': lambda _: cfg_btn(
                   'Add a New Infrastructure Provider'),
                'infrastructure_provider_discover': lambda _: cfg_btn(
                    'Discover Infrastructure Providers'),
                'infrastructure_provider': [lambda ctx: sel.click(Quadicon(ctx['provider'].name,
                                                                      'infra_prov')),
                                   {'infrastructure_provider_edit':
                                    lambda _: cfg_btn('Edit this Infrastructure Provider'),
                                    'infrastructure_provider_policy_assignment':
                                    lambda _: pol_btn('Manage Policies'),
                                    'infrastructure_provider_timelines':
                                    lambda _: mon_btn('Timelines')}]})


class Provider(Updateable, Pretty):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.

    Args:
        name: Name of the provider.
        details: a details record (see VMwareDetails, RHEVMDetails inner class).
        credentials (Credential): see Credential inner class.
        key: The CFME key of the provider in the yaml.
        candu: C&U credentials if this is a RHEVMDetails class.

    Usage:

        myprov = VMwareProvider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """
    pretty_attr = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']

    def __init__(self, name=None, credentials=None, key=None, zone=None, candu=None):
        self.name = name
        self.credentials = credentials
        self.key = key
        self.zone = zone
        self.candu = candu

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}

    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using C & U database type credential, candu = True"""

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.candu = kwargs.get('candu')

    def _submit(self, cancel, submit_button):
        if cancel:
            form_buttons.cancel()
            # sel.wait_for_element(page.configuration_btn)
        else:
            submit_button()
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
        sel.force_navigate('infrastructure_provider_new')
        fill(properties_form, self._form_mapping(True, **self.__dict__))
        fill(credential_form, self.credentials, validate=validate_credentials)
        fill(credential_form, self.candu, validate=validate_credentials)
        self._submit(cancel, add_infra_provider)
        if not cancel:
            flash.assert_message_match('Infrastructure Providers "%s" was saved' % self.name)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        sel.force_navigate('infrastructure_provider_edit', context={'provider': self})
        fill(properties_form, self._form_mapping(**updates))
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)
        fill(credential_form, updates.get('candu', None), validate=validate_credentials)
        self._submit(cancel, form_buttons.save)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('Infrastructure Provider "%s" was saved' % name)

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_provider', context={'provider': self})
        cfg_btn('Remove this Infrastructure Provider from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        if not cancel:
            flash.assert_message_match(
                'Delete initiated for 1 Infrastructure Provider from the CFME Database')

    def validate(self):
        """ Validates that the detail page matches the Providers information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. The details page is then refreshed
        continuously until the matching of all items is complete. A error will be raised
        if the match is not complete within a certain defined time period.
        """

        if not self._on_detail_page():
            sel.force_navigate('infrastructure_provider', context={'provider': self})

        client = self.get_mgmt_system()

        # Bail out here if the stats match.
        if self._do_stats_match(client, self.STATS_TO_MATCH):
            client.disconnect()
            return

        refresh_timer = RefreshTimer()

        # Otherwise refresh relationships and hand off to wait_for
        tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert()

        ec, tc = wait_for(self._do_stats_match,
                          [client, self.STATS_TO_MATCH, refresh_timer],
                          message="do_stats_match",
                          fail_func=sel.refresh,
                          num_sec=1000,
                          delay=10)
        client.disconnect()

    def refresh_provider_relationships(self):
        """Clicks on Refresh relationships button in provider"""
        sel.force_navigate('infrastructure_provider', context={"provider": self})
        tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def get_yaml_data(self):
        """ Returns yaml data for this provider.
        """
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get yaml data')
        else:
            return conf.cfme_data['management_systems'][self.key]

    def get_mgmt_system(self):
        """ Returns the mgmt_system using the :py:func:`utils.providers.provider_factory` method.
        """
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')
        else:
            return provider_factory(self.key)

    def _load_details(self):
        if not self._on_detail_page():
            sel.force_navigate('infrastructure_provider', context={'provider': self})

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self._load_details()
        return details_page.infoblock.text(*ident)

    def _do_stats_match(self, client, stats_to_match=None, refresh_timer=None):
        """ A private function to match a set of statistics, with a Provider.

        This function checks if the list of stats match, if not, the page is refreshed.

        Note: Provider mgmt_system uses the same key names as this Provider class to avoid
            having to map keyname/attributes e.g. ``num_template``, ``num_vm``.

        Args:
            client: A provider mgmt_system instance.
            stats_to_match: A list of key/attribute names to match.

        Raises:
            KeyError: If the host stats does not contain the specified key.
            ProviderHasNoProperty: If the provider does not have the property defined.
        """
        host_stats = client.stats(*stats_to_match)

        if refresh_timer:
            if refresh_timer.is_it_time():
                logger.info(' Time for a refresh!')
                tb.select("Configuration", "Refresh Relationships and Power States",
                          invokes_alert=True)
                sel.handle_alert(cancel=False)
                refresh_timer.reset()

        for stat in stats_to_match:
            try:
                cfme_stat = getattr(self, stat)
                logger.info(' Matching stat [%s], Host(%s), CFME(%s)' %
                            (stat, host_stats[stat], cfme_stat))
                if host_stats[stat] != cfme_stat:
                    return False
            except KeyError:
                raise HostStatsNotContains("Host stats information does not contain '%s'" % stat)
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '%s'" % stat)
        else:
            return True

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s (Summary)")]' % self.name)

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

    @property
    def exists(self):
        sel.force_navigate('infrastructure_providers')
        for page in paginator.pages():
            if sel.is_displayed(Quadicon(self.name, 'infra_prov')):
                return True
        else:
            return False

    def load_all_provider_vms(self):
        """ Loads the list of VMs that are running under the provider. """
        sel.force_navigate('infrastructure_provider', context={'provider': self})
        sel.click(details_page.infoblock.element("Relationships", "VMs"))

    def load_all_provider_templates(self):
        """ Loads the list of templates that are running under the provider. """
        sel.force_navigate('infrastructure_provider', context={'provider': self})
        sel.click(details_page.infoblock.element("Relationships", "Templates"))

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this Provider.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this Provider.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        sel.force_navigate('infrastructure_provider_policy_assignment', context={'provider': self})
        for policy_profile in policy_profile_names:
            if assign:
                manage_policies_tree.check_node(policy_profile)
            else:
                manage_policies_tree.uncheck_node(policy_profile)
        form_buttons.save()


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


class SCVMMProvider(Provider):
    STATS_TO_MATCH = ['num_template', 'num_vm']

    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, sec_protocol=None, sec_realm=None):
        super(SCVMMProvider, self).__init__(name=name, credentials=credentials, zone=zone, key=key)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol
        self.sec_realm = sec_realm

    def _form_mapping(self, create=None, **kwargs):

        values = version.pick({
                                    version.LOWEST: {
                                        'name_text': kwargs.get('name'),
                                        'type_select': create and 'Microsoft System Center VMM',
                                        'hostname_text': kwargs.get('hostname'),
                                        'ipaddress_text': kwargs.get('ip_address')},
                                    "5.3.1": {
                                        'name_text': kwargs.get('name'),
                                        'type_select': create and 'Microsoft System Center VMM',
                                        'hostname_text': kwargs.get('hostname'),
                                        'ipaddress_text': kwargs.get('ip_address'),
                                        'sec_protocol': kwargs.get('sec_protocol')}
                                    })

        if 'sec_protocol' in values and values['sec_protocol'] is 'Kerberos':
            values['sec_realm'] = kwargs.get('sec_realm')

        return values

    class Credential(Provider.Credential):
        # SCVMM needs to deal with domain
        def __init__(self, **kwargs):
            self.domain = kwargs.pop('domain', None)
            super(SCVMMProvider.Credential, self).__init__(**kwargs)


class RHEVMProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, start_ip=None, end_ip=None, candu=None):
        super(RHEVMProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key)

        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.candu = candu

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Red Hat Enterprise Virtualization Manager',
                'hostname_text': kwargs.get('hostname'),
                'api_port': kwargs.get('api_port'),
                'ipaddress_text': kwargs.get('ip_address')}


@fill.method((Form, Provider.Credential))
def _fill_credential(form, cred, validate=None):
    """How to fill in a credential (either candu or default).  Validates the
    credential if that option is passed in.
    """
    if cred.candu:
        fill(credential_form, {'candu_button': True,
                               'candu_principal': cred.principal,
                               'candu_secret': cred.secret,
                               'candu_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    else:
        fill(credential_form, {'default_principal': cred.principal,
                               'default_secret': cred.secret,
                               'default_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    if validate:
        flash.assert_no_errors()


@fill.method((Form, SCVMMProvider.Credential))
def _fill_scvmm_credential(form, cred, validate=None):
    fill(
        credential_form,
        {
            'default_principal': r'{}\{}'.format(cred.domain, cred.principal),
            'default_secret': cred.secret,
            'default_verify_secret': cred.verify_secret,
            'validate_btn': validate
        }
    )
    if validate:
        flash.assert_no_errors()


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        sel.force_navigate('infrastructure_providers')
    providers = set([])
    link_marker = version.pick({
        version.LOWEST: "ext_management_system",
        "5.2.5": "ems_infra"
    })
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'{}/show')]".format(link_marker)):
            providers.add(sel.get_attribute(title, "title"))
    return providers


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
    prov_type = prov_config.get('type')
    if prov_type == 'virtualcenter':
        return VMwareProvider(name=prov_config['name'],
                              hostname=prov_config['hostname'],
                              ip_address=prov_config['ipaddress'],
                              credentials=credentials,
                              zone=prov_config['server_zone'],
                              key=provider_config_name,
                              start_ip=prov_config['discovery_range']['start'],
                              end_ip=prov_config['discovery_range']['end'])
    elif prov_type == 'scvmm':
        creds = conf.credentials[prov_config['credentials']]
        credentials = SCVMMProvider.Credential(
            principal=creds['username'],
            secret=creds['password'],
            domain=creds['domain'],)
        return SCVMMProvider(
            name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials=credentials,
            key=provider_config_name,
            start_ip=prov_config['discovery_range']['start'],
            end_ip=prov_config['discovery_range']['end'],
            sec_protocol=prov_config['sec_protocol'],
            sec_realm=prov_config['sec_realm'])
    elif prov_type == 'rhevm':
        if prov_config.get('candu_credentials', None):
            candu_credentials = get_credentials_from_config(prov_config['candu_credentials'])
            candu_credentials.candu = True
        else:
            candu_credentials = None
        return RHEVMProvider(name=prov_config['name'],
                             hostname=prov_config['hostname'],
                             ip_address=prov_config['ipaddress'],
                             api_port='',
                             credentials=credentials,
                             candu=candu_credentials,
                             zone=prov_config['server_zone'],
                             key=provider_config_name,
                             start_ip=prov_config['discovery_range']['start'],
                             end_ip=prov_config['discovery_range']['end'])
    else:
        raise UnknownProviderType('{} is not a known infra provider type'.format(prov_type))


def discover_from_provider(provider_data):
    """
    Begins provider discovery from a provider instance

    Usage:
        discover_from_config(provider.get_from_config('rhevm'))
    """
    vmware = isinstance(provider_data, VMwareProvider)
    rhevm = isinstance(provider_data, RHEVMProvider)
    scvmm = isinstance(provider_data, SCVMMProvider)
    discover(rhevm, vmware, scvmm, cancel=False, start_ip=provider_data.start_ip,
             end_ip=provider_data.end_ip)


def discover(rhevm=False, vmware=False, scvmm=False, cancel=False, start_ip=None, end_ip=None):
    """
    Discover infrastructure providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
        rhvem: Whether to scan for RHEVM providers
        vmware: Whether to scan for VMware providers
        scvmm: Whether to scan for SCVMM providers
        cancel:  Whether to cancel out of the discover UI.
    """
    sel.force_navigate('infrastructure_provider_discover')
    form_data = {}
    if rhevm:
        form_data.update({'rhevm_chk': True})
    if vmware:
        form_data.update({'vmware_chk': True})
    if scvmm:
        form_data.update({'scvmm_chk': True})

    if start_ip:
        for idx, octet in enumerate(start_ip.split('.')):
            key = 'from_%i' % idx
            form_data.update({key: octet})
    if end_ip:
        end_octet = end_ip.split('.')[-1]
        form_data.update({'to_3': end_octet})

    fill(discover_form, form_data,
         action=form_buttons.cancel if cancel else discover_form.start_button,
         action_always=True)


def wait_for_a_provider():
    sel.force_navigate('infrastructure_providers')
    logger.info('Waiting for a provider to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any provider to appear",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_provider_delete(provider):
    sel.force_navigate('infrastructure_providers')
    quad = Quadicon(provider.name, 'infra_prov')
    logger.info('Waiting for a provider to delete...')
    wait_for(lambda prov: not sel.is_displayed(prov), func_args=[quad], fail_condition=False,
             message="Wait provider to disappear", num_sec=1000, fail_func=sel.refresh)
