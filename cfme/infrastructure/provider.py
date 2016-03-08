""" A model of an Infrastructure Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var candu_form: A :py:class:`cfme.web_ui.Form` object describing the C&U credentials form.
"""
from functools import partial

from utils.db import cfmedb
import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.host import Host
from cfme.web_ui.menu import nav
import cfme.web_ui.toolbar as tb
from cfme.common.provider import CloudInfraProvider
import utils.conf as conf
from cfme.web_ui import (
    Region, Quadicon, Form, Select, CheckboxTree, fill, form_buttons, paginator, Input,
    AngularSelect
)
from cfme.web_ui.form_buttons import FormButton
from utils.api import rest_api
from utils.log import logger
from utils.wait import wait_for
from utils import version
from utils.pretty import Pretty
from utils.varmeth import variable


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
        ('type_select', {version.LOWEST: Select('select#server_emstype'),
                         '5.5': AngularSelect("server_emstype")}),
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('api_port', Input("port")),
        ('sec_protocol', {version.LOWEST: Select("select#security_protocol"),
                         '5.5': AngularSelect("security_protocol")}),
        ('sec_realm', Input("realm"))
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


class Provider(Pretty, CloudInfraProvider):
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
    instances_page_name = "infra_vm_and_templates"
    quad_name = "infra_prov"
    properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Infrastructure Provider")
    save_button = form_buttons.FormButton("Save Changes")

    def __init__(
            self, name=None, credentials=None, key=None, zone=None, provider_data=None):
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.provider_data = provider_data
        self.zone = zone
        self.vm_name = version.pick({version.LOWEST: "VMs", '5.5': "VMs and Instances"})
        self.template_name = "Templates"

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}

    @variable(alias='db')
    def num_datastore(self):
        storage_table_name = version.pick({version.LOWEST: 'hosts_storages',
                                           '5.5.0.8': 'host_storages'})
        """ Returns the providers number of templates, as shown on the Details page."""

        results = list(cfmedb().engine.execute(
            'SELECT DISTINCT storages.name, hosts.ems_id '
            'FROM ext_management_systems, hosts, storages, {} '
            'WHERE hosts.id={}.host_id AND '
            'storages.id={}.storage_id AND '
            'hosts.ems_id=ext_management_systems.id AND '
            'ext_management_systems.name=\'{}\''.format(storage_table_name,
                                                        storage_table_name, storage_table_name,
                                                        self.name)))
        return len(results)

    @num_datastore.variant('ui')
    def num_datastore_ui(self):
            return int(self.get_detail("Relationships", "Datastores"))

    @variable(alias='rest')
    def num_host(self):
        provider = rest_api().collections.providers.find_by(name=self.name)[0]
        num_host = 0
        for host in rest_api().collections.hosts:
            if host['ems_id'] == provider.id:
                num_host += 1
        return num_host

    @num_host.variant('db')
    def num_host_db(self):
        ext_management_systems = cfmedb()["ext_management_systems"]
        hosts = cfmedb()["hosts"]
        hostlist = list(cfmedb().session.query(hosts.name)
                        .join(ext_management_systems, hosts.ems_id == ext_management_systems.id)
                        .filter(ext_management_systems.name == self.name))
        return len(hostlist)

    @num_host.variant('ui')
    def num_host_ui(self):
        return int(self.get_detail("Relationships", "host.png", use_icon=True))

    @variable(alias='rest')
    def num_cluster(self):
        provider = rest_api().collections.providers.find_by(name=self.name)[0]
        num_cluster = 0
        for cluster in rest_api().collections.clusters:
            if cluster['ems_id'] == provider.id:
                num_cluster += 1
        return num_cluster

    @num_cluster.variant('db')
    def num_cluster_db(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = cfmedb()["ext_management_systems"]
        clusters = cfmedb()["ems_clusters"]
        clulist = list(cfmedb().session.query(clusters.name)
                       .join(ext_management_systems,
                             clusters.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name))
        return len(clulist)

    @num_cluster.variant('ui')
    def num_cluster_ui(self):
        return int(self.get_detail("Relationships", "cluster.png", use_icon=True))

    def discover(self):
        """
        Begins provider discovery from a provider instance

        Usage:
            discover_from_config(utils.providers.get_crud('rhevm'))
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


class OpenstackInfraProvider(Provider):
    STATS_TO_MATCH = ['num_template', 'num_host']

    def __init__(self, name=None, credentials=None, key=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None,
                 sec_protocol=None):
        super(OpenstackInfraProvider, self).__init__(name=name, credentials=credentials,
                                             key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenStack Platform Director',
                'hostname_text': kwargs.get('hostname'),
                'ipaddress_text': kwargs.get('ip_address'),
                'sec_protocol': kwargs.get('sec_protocol')}


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
