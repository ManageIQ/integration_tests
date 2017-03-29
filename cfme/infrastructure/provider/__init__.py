""" A model of an Infrastructure Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var candu_form: A :py:class:`cfme.web_ui.Form` object describing the C&U credentials form.
"""
from functools import partial

from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToObject

from cfme.base.ui import Server
from cfme.common.provider import CloudInfraProvider
from cfme.common.provider_views import (ProviderAddView,
                                        ProviderEditView,
                                        ProviderDetailsView,
                                        ProviderTimelinesView,
                                        ProvidersDiscoverView,
                                        ProvidersManagePoliciesView,
                                        ProvidersEditTagsView,
                                        ProvidersView)
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.cluster import Cluster
from cfme.infrastructure.host import Host
from cfme.web_ui import Quadicon, paginator, toolbar as tb, match_location
from utils import conf, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.varmeth import variable
from utils.wait import wait_for

match_page = partial(match_location, controller='ems_infra', title='Infrastructure Providers')
cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')


class InfraProvider(Pretty, CloudInfraProvider):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.

    Args:
        name: Name of the provider.
        details: a details record (see VMwareDetails, RHEVMDetails inner class).
        credentials (:py:class:`Credential`): see Credential inner class.
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
    category = "infra"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    string_name = "Infrastructure"
    page_name = "infrastructure"
    templates_destination_name = "Templates"
    quad_name = "infra_prov"
    db_types = ["InfraManager"]

    def __init__(
            self, name=None, credentials=None, key=None, zone=None, provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.provider_data = provider_data
        self.zone = zone
        self.template_name = "Templates"

    def _form_mapping(self, create=None, **kwargs):
        return {'name': kwargs.get('name')}

    @cached_property
    def vm_name(self):
        return version.pick({
            version.LOWEST: "VMs and Instances",
            '5.7.1': "Virtual Machines"})

    @variable(alias='db')
    def num_datastore(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        results = list(self.appliance.db.engine.execute(
            'SELECT DISTINCT storages.name, hosts.ems_id '
            'FROM ext_management_systems ems, hosts, storages st, host_storages hst'
            'WHERE hosts.id=hst.host_id AND '
            'st.id=hst.storage_id AND '
            'hosts.ems_id=ems.id AND '
            'ems.name=\'{}\''.format(self.name)))
        return len(results)

    @num_datastore.variant('ui')
    def num_datastore_ui(self):
            return int(self.get_detail("Relationships", "Datastores"))

    @variable(alias='rest')
    def num_host(self):
        provider = self.appliance.rest_api.collections.providers.find_by(name=self.name)[0]
        num_host = 0
        for host in self.appliance.rest_api.collections.hosts:
            if host['ems_id'] == provider.id:
                num_host += 1
        return num_host

    @num_host.variant('db')
    def num_host_db(self):
        ext_management_systems = self.appliance.db["ext_management_systems"]
        hosts = self.appliance.db["hosts"]
        hostlist = list(self.appliance.db.session.query(hosts.name)
                        .join(ext_management_systems, hosts.ems_id == ext_management_systems.id)
                        .filter(ext_management_systems.name == self.name))
        return len(hostlist)

    @num_host.variant('ui')
    def num_host_ui(self):
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
        provider = self.appliance.rest_api.collections.providers.find_by(name=self.name)[0]
        num_cluster = 0
        for cluster in self.appliance.rest_api.collections.clusters:
            if cluster['ems_id'] == provider.id:
                num_cluster += 1
        return num_cluster

    @num_cluster.variant('db')
    def num_cluster_db(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = self.appliance.db["ext_management_systems"]
        clusters = self.appliance.db["ems_clusters"]
        clulist = list(self.appliance.db.session.query(clusters.name)
                       .join(ext_management_systems,
                             clusters.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name))
        return len(clulist)

    @num_cluster.variant('ui')
    def num_cluster_ui(self):
        return int(self.get_detail("Relationships", "cluster-", use_icon=True))

    def discover(self):  # todo: move this to provider collections
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
    def id(self):
        """
        returns current provider id using rest api
        """
        return self.appliance.rest_api.collections.providers.find_by(name=self.name)[0].id

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
            result.append(Host(name=host["name"],
                               credentials=cred,
                               provider=self))
        return result

    def get_clusters(self):
        """returns the list of clusters belonging to the provider"""
        web_clusters = []
        view = navigate_to(self, 'Details')
        # todo: create nav location + view later
        view.contents.relationships.click_at('Clusters')
        icons = Quadicon.all(qtype='cluster')
        for icon in icons:
            web_clusters.append(Cluster(icon.name, self))
        return web_clusters


@navigator.register(Server, 'InfraProviders')
@navigator.register(InfraProvider, 'All')
class All(CFMENavigateStep):
    VIEW = ProvidersView
    prerequisite = NavigateToObject(Server, 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        paginator = self.view.paginator
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(InfraProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = ProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg = self.prerequisite_view.toolbar.configuration
        cfg.item_select('Add a New Infrastructure Provider')


@navigator.register(InfraProvider, 'Discover')
class Discover(CFMENavigateStep):
    VIEW = ProvidersDiscoverView
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg = self.prerequisite_view.toolbar.configuration
        cfg.item_select('Discover Infrastructure Providers')


@navigator.register(InfraProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = ProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def resetter(self):
        # Reset view and selection
        if version.current_version() >= '5.7':  # no view selector in 5.6
            view_selector = self.view.toolbar.view_selector
            if view_selector.selected != 'Summary View':
                view_selector.select('Summary View')


@navigator.register(InfraProvider, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Manage Policies')


@navigator.register(InfraProvider, 'ManagePoliciesFromDetails')
class ManagePoliciesFromDetails(CFMENavigateStep):
    VIEW = ProvidersManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(InfraProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = ProvidersEditTagsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(InfraProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = ProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        cfg = self.prerequisite_view.toolbar.configuration
        cfg.item_select('Edit Selected Infrastructure Providers')


@navigator.register(InfraProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = ProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon = self.prerequisite_view.toolbar.monitoring
        mon.item_select('Timelines')


@navigator.register(InfraProvider, 'Instances')
class Instances(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (All VMs)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        self.prerequisite_view.contents.relationships.click_at('VMs and Instances')
        # todo: add vms view when it is done


@navigator.register(InfraProvider, 'Templates')
class Templates(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (All Templates)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        self.prerequisite_view.contents.relationships.click_at('Templates')
        # todo: add templates view when it is done


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        navigate_to(InfraProvider, 'All')
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
        rhevm: Whether to scan for RHEVM providers
        vmware: Whether to scan for VMware providers
        scvmm: Whether to scan for SCVMM providers
        cancel:  Whether to cancel out of the discover UI.
        start_ip: String start of the IP range for discovery
        end_ip: String end of the IP range for discovery
    """
    form_data = {}
    if rhevm:
        form_data.update({'rhevm': True})
    if vmware:
        form_data.update({'vmware': True})
    if scvmm:
        form_data.update({'scvmm': True})

    if start_ip:
        for idx, octet in enumerate(start_ip.split('.'), start=1):
            key = 'from_ip{idx}'.format(idx=idx)
            form_data.update({key: octet})
    if end_ip:
        end_octet = end_ip.split('.')[-1]
        form_data.update({'to_ip4': end_octet})

    view = navigate_to(InfraProvider, 'Discover')
    view.fill(form_data)
    if cancel:
        view.cancel.click()
    else:
        view.start.click()


def wait_for_a_provider():
    navigate_to(InfraProvider, 'All')
    logger.info('Waiting for a provider to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any provider to appear",
             num_sec=1000, fail_func=sel.refresh)
