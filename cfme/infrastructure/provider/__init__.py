""" A model of an Infrastructure Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var candu_form: A :py:class:`cfme.web_ui.Form` object describing the C&U credentials form.
"""
from functools import partial

from cfme.common.provider import CloudInfraProvider, import_all_modules_of
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.host import Host
from cfme.web_ui import (
    Region, Quadicon, Form, Select, CheckboxTree, fill, form_buttons, paginator, Input,
    AngularSelect, toolbar as tb, Radio
)
from cfme.web_ui.form_buttons import FormButton
from cfme.web_ui.menu import nav
from cfme.web_ui.tabstrip import TabStripForm
from utils import conf, deferred_verpick, version
from utils.api import rest_api
from utils.db import cfmedb
from utils.log import logger
from utils.pretty import Pretty
from utils.varmeth import variable
from utils.wait import wait_for


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
        ('type_select', {
            version.LOWEST: Select('select#server_emstype'),
            '5.5': AngularSelect("server_emstype")
        }),
        ('name_text', Input("name")),
        ('hostname_text', {version.LOWEST: Input("hostname")}),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('api_port', Input("port")),
        ('sec_protocol', {version.LOWEST: Select("select#security_protocol"),
            '5.5': AngularSelect("security_protocol", exact=True)}),
        ('sec_realm', Input("realm"))
    ])


properties_form_56 = TabStripForm(
    fields=[
        ('type_select', AngularSelect("emstype")),
        ('name_text', Input("name")),
        ("api_version", AngularSelect("api_version")),
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('api_port', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol", exact=True)),
        ],
        "Events": [
            ('event_selection', Radio('event_stream_selection')),
            ('amqp_hostname_text', Input("amqp_hostname")),
            ('amqp_api_port', Input("amqp_api_port")),
            ('amqp_sec_protocol', AngularSelect("amqp_security_protocol", exact=True)),
        ],
        "C & U Database": [
            ('candu_hostname_text', Input("metrics_hostname")),
            ('acandu_api_port', Input("metrics_api_port")),
        ]
    })


prop_region = Region(
    locators={
        'properties_form': {
            version.LOWEST: properties_form,
            '5.6': properties_form_56,
        }
    }
)

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

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


@CloudInfraProvider.add_base_type
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
    provider_types = {}
    in_version = (version.LOWEST, version.LATEST)
    type_tclass = "infra"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    string_name = "Infrastructure"
    page_name = "infrastructure"
    instances_page_name = "infra_vm_and_templates"
    templates_page_name = "infra_vm_and_templates"
    quad_name = "infra_prov"
    _properties_region = prop_region  # This will get resolved in common to a real form
    add_provider_button = deferred_verpick({
        version.LOWEST: form_buttons.FormButton("Add this Infrastructure Provider"),
        '5.6': form_buttons.add
    })
    save_button = deferred_verpick({
        version.LOWEST: form_buttons.save,
        '5.6': form_buttons.angular_save
    })

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
        if version.current_version() < "5.6":
            host_src = "host.png"
            node_src = "node.png"
        else:
            host_src = "host-"
            node_src = "node-"

        try:
            num = int(self.get_detail("Relationships", host_src, use_icon=True))
        except sel.NoSuchElementException:
            logger.error("Couldn't find number of hosts using key [Hosts] trying Nodes")
            num = int(self.get_detail("Relationships", node_src, use_icon=True))
        return num

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
        if version.current_version() < "5.6":
            return int(self.get_detail("Relationships", "cluster.png", use_icon=True))
        else:
            return int(self.get_detail("Relationships", "cluster-", use_icon=True))

    def discover(self):
        """
        Begins provider discovery from a provider instance

        Usage:
            discover_from_config(utils.providers.get_crud('rhevm'))
        """
        from virtualcenter import VMwareProvider
        from rhevm import RHEVMProvider
        from scvmm import SCVMMProvider
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


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        sel.force_navigate('infrastructure_providers')
    providers = set([])
    link_marker = "ems_infra"
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

import_all_modules_of('cfme.infrastructure.provider')
