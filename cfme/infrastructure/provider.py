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
from utils.db import cfmedb
import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.host import Host
import cfme.web_ui.flash as flash
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
import cfme.web_ui.toolbar as tb
from cfme.common.provider import BaseProvider
import utils.conf as conf
from cfme.exceptions import UnknownProviderType
from cfme.web_ui import (
    Region, Quadicon, Form, Select, CheckboxTree, fill, form_buttons, paginator, Input
)
from cfme.web_ui.form_buttons import FormButton
from utils.browser import ensure_browser_open
from utils.log import logger
from utils.update import Updateable
from utils.wait import wait_for
from utils import version
from utils.pretty import Pretty
from utils.signals import fire

add_infra_provider = FormButton("Add this Infrastructure Provider")

details_page = Region(infoblock_type='detail')

# Forms
discover_form = Form(
    fields=[
        ('rhevm_chk', Input("discover_type_rhevm")),
        ('vmware_chk', Input("discover_type_virtualcenter")),
        ('scvmm_chk', Input("discover_type_scvmm")),
        ('from_0', Input("from_first")),
        ('from_1', Input("from_second")),
        ('from_2', Input("from_third")),
        ('from_3', Input("from_fourth")),
        ('to_3', Input("to_fourth")),
        ('start_button', FormButton("Start the Host Discovery"))
    ])

properties_form = Form(
    fields=[
        ('type_select', Select("select#server_emstype")),
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('api_port', Input("port")),
        ('sec_protocol', Select("select#security_protocol")),
        ('sec_realm', Input("realm"))
    ])

credential_form = Form(
    fields=[
        ('default_button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('default_principal', Input("default_userid")),
        ('default_secret', Input("default_password")),
        ('default_verify_secret', Input("default_verify")),
        ('candu_button', "//div[@id='auth_tabs']/ul/li/a[@href='#metrics']"),
        ('candu_principal', Input("metrics_userid")),
        ('candu_secret', Input("metrics_password")),
        ('candu_verify_secret', Input("metrics_verify")),
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


class Provider(Updateable, Pretty, BaseProvider):
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
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    string_name = "Infrastructure"
    page_name = "infrastructure"
    quad_name = "infra_prov"
    vm_name = "VMs"
    template_name = "Templates"

    def __init__(
            self, name=None, credentials=None, key=None, zone=None, provider_data=None):
        self.name = name
        self.credentials = credentials
        self.key = key
        self.provider_data = provider_data
        self.zone = zone

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}

    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using C & U database type credential, candu = True"""

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.candu = kwargs.get('candu')

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
        for cred in self.credentials:
            fill(credential_form, self.credentials[cred], validate=validate_credentials)
        self._submit(cancel, add_infra_provider)
        fire("providers_changed")
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
        for cred in self.credentials:
            fill(credential_form, updates.get('credentials', {}).get(cred, None),
                 validate=validate_credentials)
        self._submit(cancel, form_buttons.save)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('Infrastructure Provider "%s" was saved' % name)

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s (Summary)")]' % self.name)

    def num_datastore(self, db=True):
        """ Returns the providers number of templates, as shown on the Details page."""
        if db:
            results = list(cfmedb().engine.execute(
                'SELECT DISTINCT storages.name, hosts.ems_id '
                'FROM ext_management_systems, hosts, storages, hosts_storages '
                'WHERE hosts.id=hosts_storages.host_id AND '
                'storages.id=hosts_storages.storage_id AND '
                'hosts.ems_id=ext_management_systems.id AND '
                'ext_management_systems.name=\'{}\''.format(self.name)))
            return len(results)
        else:
            return int(self.get_detail("Relationships", "Datastores"))

    def num_host(self, db=True):
        """ Returns the providers number of instances, as shown on the Details page."""
        if db:
            ext_management_systems = cfmedb()["ext_management_systems"]
            hosts = cfmedb()["hosts"]
            hostlist = list(cfmedb().session.query(hosts.name)
                            .join(ext_management_systems, hosts.ems_id == ext_management_systems.id)
                            .filter(ext_management_systems.name == self.name))
            return len(hostlist)
        else:
            return int(self.get_detail("Relationships", "Hosts"))

    def num_cluster(self, db=True):
        """ Returns the providers number of templates, as shown on the Details page."""
        if db:
            ext_management_systems = cfmedb()["ext_management_systems"]
            clusters = cfmedb()["ems_clusters"]
            clulist = list(cfmedb().session.query(clusters.name)
                           .join(ext_management_systems,
                                 clusters.ems_id == ext_management_systems.id)
                           .filter(ext_management_systems.name == self.name))
            return len(clulist)
        else:
            return int(self.get_detail("Relationships", "Clusters"))

    def discover(self):
        """
        Begins provider discovery from a provider instance

        Usage:
            discover_from_config(provider.get_from_config('rhevm'))
        """
        vmware = isinstance(self, VMwareProvider)
        rhevm = isinstance(self, RHEVMProvider)
        scvmm = isinstance(self, SCVMMProvider)
        discover(rhevm, vmware, scvmm, cancel=False, start_ip=self.start_ip,
                 end_ip=self.end_ip)

    @property
    def hosts(self):
        """Returns list of :py:class:`cfme.infrastructure.host.Host` that should belong to this
        provider according to the YAML
        """
        result = []
        for host in self.get_yaml_data().get("hosts", []):
            creds = conf.credentials.get(host["credentials"], {})
            cred = Host.Credential(
                principal=creds["username"],
                secret=creds["password"],
                verify_secret=creds["password"],
            )
            result.append(Host(name=host["name"], credentials=cred))
        return result

    def load_all_provider_vms(self):
        """ Loads the list of VMs that are running under the provider. """
        sel.force_navigate('infrastructure_provider', context={'provider': self})
        sel.click(details_page.infoblock.element("Relationships", "VMs"))

    def load_all_provider_templates(self):
        """ Loads the list of templates that are running under the provider. """
        sel.force_navigate('infrastructure_provider', context={'provider': self})
        sel.click(details_page.infoblock.element("Relationships", "Templates"))


class VMwareProvider(Provider):
    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None):
        super(VMwareProvider, self).__init__(name=name, credentials=credentials,
                                             zone=zone, key=key, provider_data=provider_data)

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
                 ip_address=None, start_ip=None, end_ip=None, sec_protocol=None, sec_realm=None,
                 provider_data=None):
        super(SCVMMProvider, self).__init__(name=name, credentials=credentials,
            zone=zone, key=key, provider_data=provider_data)

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
                 ip_address=None, api_port=None, start_ip=None, end_ip=None,
                 provider_data=None):
        super(RHEVMProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key, provider_data=provider_data)

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

    prov_config = conf.cfme_data.get('management_systems', {})[provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    prov_type = prov_config.get('type')

    if prov_config.get('discovery_range', None):
        start_ip = prov_config['discovery_range']['start']
        end_ip = prov_config['discovery_range']['end']
    else:
        start_ip = prov_config['ipaddress']
        end_ip = prov_config['ipaddress']

    if prov_type == 'virtualcenter':
        return VMwareProvider(name=prov_config['name'],
                              hostname=prov_config['hostname'],
                              ip_address=prov_config['ipaddress'],
                              credentials={'default': credentials},
                              zone=prov_config['server_zone'],
                              key=provider_config_name,
                              start_ip=start_ip,
                              end_ip=end_ip)
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
            credentials={'default': credentials},
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip,
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
                             credentials={'default': credentials,
                                          'candu': candu_credentials},
                             zone=prov_config['server_zone'],
                             key=provider_config_name,
                             start_ip=start_ip,
                             end_ip=end_ip)
    else:
        raise UnknownProviderType('{} is not a known infra provider type'.format(prov_type))


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
