""" A model of an Infrastructure Provider in CFME
"""
from widgetastic.utils import Fillable

from cached_property import cached_property
from cfme.exceptions import DestinationNotFound
from navmazing import NavigateToSibling, NavigateToObject
from widgetastic_manageiq import BreadCrumb, BaseEntitiesView, View

from cfme.base.ui import Server
from cfme.common import TagPageView
from cfme.common.provider import CloudInfraProvider
from cfme.common.provider_views import (InfraProviderAddView,
                                        InfraProviderEditView,
                                        InfraProviderDetailsView,
                                        ProviderTimelinesView,
                                        InfraProvidersDiscoverView,
                                        ProvidersManagePoliciesView,
                                        InfraProvidersView,
                                        ProviderNodesView)
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.cluster import ClusterView, ClusterToolbar
from cfme.infrastructure.host import Host
from cfme.utils import conf, version
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for


class ProviderClustersView(ClusterView):
    """The all view page for clusters open from provider detail page"""
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == '{p}(All Clusters)'.format(p=self.context['object'].name))

    toolbar = View.nested(ClusterToolbar)
    breadcrumb = BreadCrumb()
    including_entities = View.include(BaseEntitiesView, use_parent=True)


class InfraProvider(Pretty, CloudInfraProvider, Fillable):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.

    Args:
        name: Name of the provider.
        details: a details record (see VMwareDetails, RHEVMDetails inner class).
        key: The CFME key of the provider in the yaml.
        endpoints: one or several provider endpoints like DefaultEndpoint. it should be either dict
        in format dict{endpoint.name, endpoint, endpoint_n.name, endpoint_n}, list of endpoints or
        mere one endpoint
    Usage:
        credentials = Credential(principal='bad', secret='reallybad')
        endpoint = DefaultEndpoint(hostname='some_host', api_port=65536, credentials=credentials)
        myprov = VMwareProvider(name='foo',
                             region='us-west-1'
                             endpoints=endpoint)
        myprov.create()

    """
    provider_types = {}
    category = "infra"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    string_name = "Infrastructure"
    page_name = "infrastructure"
    templates_destination_name = "Templates"
    db_types = ["InfraManager"]
    hosts_menu_item = "Hosts"

    def __init__(
            self, name=None, endpoints=None, key=None, zone=None, provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.endpoints = self._prepare_endpoints(endpoints)
        self.key = key
        self.provider_data = provider_data
        self.zone = zone
        self.template_name = "Templates"

    @cached_property
    def vm_name(self):
        return version.pick({
            version.LOWEST: "VMs and Instances",
            '5.7.1': "Virtual Machines"})

    @variable(alias='db')
    def num_datastore(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        results = list(self.appliance.db.client.engine.execute(
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
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        hosts = self.appliance.db.client["hosts"]
        hostlist = list(self.appliance.db.client.session.query(hosts.name)
                        .join(ext_management_systems, hosts.ems_id == ext_management_systems.id)
                        .filter(ext_management_systems.name == self.name))
        return len(hostlist)

    @num_host.variant('ui')
    def num_host_ui(self):
        try:
            num = self.get_detail("Relationships", 'Hosts')
        except sel.NoSuchElementException:
            logger.error("Couldn't find number of hosts using key [Hosts] trying Nodes")
            num = self.get_detail("Relationships", 'Nodes')
        return int(num)

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
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        clusters = self.appliance.db.client["ems_clusters"]
        clulist = list(self.appliance.db.client.session.query(clusters.name)
                       .join(ext_management_systems,
                             clusters.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name))
        return len(clulist)

    @num_cluster.variant('ui')
    def num_cluster_ui(self):
        num = self.get_detail("Relationships", 'Clusters')
        return int(num)

    def discover(self):  # todo: move this to provider collections
        """
        Begins provider discovery from a provider instance

        Usage:
            discover_from_config(utils.providers.get_crud('rhevm'))
        """
        discover(self, cancel=False, start_ip=self.start_ip, end_ip=self.end_ip)

    @property
    def hosts(self):
        """Returns list of :py:class:`cfme.infrastructure.host.Host` that should belong to this
        provider according to the YAML
        """
        result = []
        host_collection = self.appliance.collections.hosts
        for host in self.get_yaml_data().get("hosts", []):
            creds = conf.credentials.get(host["credentials"], {})
            cred = Host.Credential(
                principal=creds["username"],
                secret=creds["password"],
                verify_secret=creds["password"],
            )

            result.append(host_collection.instantiate(name=host["name"], credentials=cred,
                                                      provider=self))
        return result

    def get_clusters(self):
        """returns the list of clusters belonging to the provider"""
        view = navigate_to(self, 'Clusters')
        col = self.appliance.collections.clusters
        return [col.instantiate(e.name, self) for e in view.entities.get_all(surf_pages=True)]

    def as_fill_value(self):
        return self.name

    @property
    def view_value_mapping(self):
        return {'name': self.name}


@navigator.register(Server, 'InfraProviders')
@navigator.register(InfraProvider, 'All')
class All(CFMENavigateStep):
    VIEW = InfraProvidersView
    prerequisite = NavigateToObject(Server, 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        paginator = self.view.entities.paginator
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(InfraProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = InfraProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New '
                                                                 'Infrastructure Provider')


@navigator.register(InfraProvider, 'Discover')
class Discover(CFMENavigateStep):
    VIEW = InfraProvidersDiscoverView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Discover '
                                                                 'Infrastructure Providers')


@navigator.register(InfraProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = InfraProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).click()

    def resetter(self):
        # Reset view and selection
        if version.current_version() >= '5.7':  # no view selector in 5.6
            view_selector = self.view.toolbar.view_selector
            if view_selector.selected != 'Summary View':
                view_selector.select('Summary View')


@navigator.register(InfraProvider, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ProvidersManagePoliciesView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(InfraProvider, 'ManagePoliciesFromDetails')
class ManagePoliciesFromDetails(CFMENavigateStep):
    VIEW = ProvidersManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(InfraProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(InfraProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = InfraProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.configuration.item_select('Edit Selected '
                                                                 'Infrastructure Providers')


@navigator.register(InfraProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = ProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon = self.prerequisite_view.toolbar.monitoring
        mon.item_select('Timelines')


@navigator.register(InfraProvider, 'Clusters')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = ProviderClustersView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.entities.relationships.click_at('Clusters')


@navigator.register(InfraProvider, 'ProviderNodes')  # matching other infra class destinations
class ProviderNodes(CFMENavigateStep):
    VIEW = ProviderNodesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        try:
            self.prerequisite_view.entities.relationships.click_at(self.obj.hosts_menu_item)
        except NameError:
            raise DestinationNotFound(
                "{} aren't present on details page of this provider"
                .format(self.obj.hosts_menu_item))


def get_all_providers():
    """Returns list of all providers"""
    view = navigate_to(InfraProvider, 'All')
    return [item.name for item in view.entities.get_all(surf_pages=True)]


def discover(discover_cls, cancel=False, start_ip=None, end_ip=None):
    """
    Discover infrastructure providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
        discover_cls: Instance of provider class
        cancel:  Whether to cancel out of the discover UI.
        start_ip: String start of the IP range for discovery
        end_ip: String end of the IP range for discovery
    """
    form_data = {}
    if discover_cls:
        form_data.update(discover_cls.discover_dict)

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
    view = navigate_to(InfraProvider, 'All')
    logger.info('Waiting for a provider to appear...')
    wait_for(lambda: int(view.entities.paginator.items_amount), fail_condition=0,
             message="Wait for any provider to appear", num_sec=1000,
             fail_func=view.browser.refresh)
