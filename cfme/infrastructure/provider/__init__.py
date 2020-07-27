""" A model of an Infrastructure Provider in CFME
"""
from typing import Type

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from varmeth import variable
from widgetastic.exceptions import MoveTargetOutOfBoundsException
from widgetastic.utils import Fillable
from widgetastic_patternfly import BreadCrumb

from cfme.base.ui import Server
from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider import BaseProvider
from cfme.common.provider import CloudInfraProviderMixin
from cfme.common.provider import provider_types
from cfme.common.provider_views import InfraProviderAddView
from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.provider_views import InfraProvidersDiscoverView
from cfme.common.provider_views import InfraProvidersView
from cfme.common.provider_views import ProviderEditView
from cfme.common.provider_views import ProviderNodesView
from cfme.common.provider_views import ProviderTemplatesView
from cfme.common.provider_views import ProviderTimelinesView
from cfme.common.provider_views import ProviderVmsView
from cfme.exceptions import DestinationNotFound
from cfme.infrastructure.cluster import ClusterToolbar
from cfme.infrastructure.cluster import ClusterView
from cfme.infrastructure.host import HostsCollection
from cfme.infrastructure.virtual_machines import InfraTemplate
from cfme.infrastructure.virtual_machines import InfraTemplateCollection
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import TBaseEntity
from cfme.optimize.utilization import ProviderUtilizationTrendsView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import NoSuchElementException
from widgetastic_manageiq import View


class ProviderClustersView(ClusterView):
    """The all view page for clusters open from provider detail page"""
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == '{p} (All Clusters)'.format(p=self.context['object'].name))

    toolbar = View.nested(ClusterToolbar)
    breadcrumb = BreadCrumb()
    including_entities = View.include(BaseEntitiesView, use_parent=True)


@attr.s(eq=False)
class InfraProvider(BaseProvider, CloudInfraProviderMixin, Pretty, Fillable,
                    PolicyProfileAssignable, Taggable):
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
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    SNAPSHOT_TITLE = 'name'  # attribute of the provider vm's snapshots used for the title
    provider_types = {}
    vm_class = InfraVm
    template_class = InfraTemplate
    category = "infra"
    pretty_attrs = ['name', 'key', 'zone']
    string_name = "Infrastructure"
    templates_destination_name = "Templates"
    template_name = "Templates"
    db_types = ["InfraManager"]
    hosts_menu_item = "Hosts"
    vm_name = "Virtual Machines"
    collection_name = 'infra_providers'
    provisioning_dialog_widget_names = BaseProvider.provisioning_dialog_widget_names.union(
        {'hardware', 'network', 'customize'})

    name = attr.ib(default=None)
    key = attr.ib(default=None)
    zone = attr.ib(default=None)
    start_ip = attr.ib(default=None)
    end_ip = attr.ib(default=None)
    provider_data = attr.ib(default=None)

    _collections = {'hosts': HostsCollection, 'infra_templates': InfraTemplateCollection}

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.parent = self.appliance.collections.infra_providers

    @variable(alias='db')
    def num_datastore(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        results = list(self.appliance.db.client.engine.execute(
            'SELECT DISTINCT storages.name, hosts.ems_id '
            'FROM ext_management_systems ems, hosts, storages st, host_storages hst '
            'WHERE hosts.id=hst.host_id AND '
            'st.id=hst.storage_id AND '
            'hosts.ems_id=ems.id AND '
            'ems.name=\'{}\''.format(self.name)))
        return len(results)

    @num_datastore.variant('ui')
    def num_datastore_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Datastores"))

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
        view = navigate_to(self, "Details")
        try:
            num = view.entities.summary("Relationships").get_text_of("Hosts")
        except NoSuchElementException:
            logger.error("Couldn't find number of hosts using key [Hosts] trying Nodes")
            num = view.entities.summary("Relationships").get_text_of("Nodes")
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
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Clusters"))

    @property
    def hosts(self):
        return self.collections.hosts

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

    def setup_hosts_credentials(self):
        """Setup credentials for all provider's hosts"""
        for host in self.hosts.all():
            host_data = None
            for data in self.data['hosts']:
                if data['name'] == host.name:
                    host_data = data
                    break
            if BZ(1718209).blocks:
                # this BZ doesn't allow us to use REST to update creds, so use UI
                with update(host, validate_credentials=True):
                    host.credentials = {
                        "default": host.Credential.from_config(host_data["credentials"]["default"])
                    }
            else:
                host.update_credentials_rest(credentials=host_data['credentials'])

    def remove_hosts_credentials(self):
        for host in self.hosts.all():
            host.remove_credentials_rest()


# todo: update all docstrings
@attr.s
class InfraProviderCollection(BaseCollection):
    """Collection object for InfraProvider object
    """

    def all(self):
        view = navigate_to(self, 'All')
        provs = view.entities.get_all(surf_pages=True)

        # trying to figure out provider type and class
        # todo: move to all providers collection later
        def _get_class(pid):
            prov_type = self.appliance.rest_api.collections.providers.get(id=pid)['type']
            for prov_class in provider_types('infra').values():
                if prov_class.db_types[0] in prov_type:
                    return prov_class

        return [self.instantiate(prov_class=_get_class(p.data['id']), name=p.name) for p in provs]

    def instantiate(self, prov_class: Type[TBaseEntity], *args, **kwargs) -> TBaseEntity:
        return prov_class.from_collection(self, *args, **kwargs)

    def create(self, prov_class, *args, **kwargs):
        # ugly workaround until I move everything to main class
        class_attrs = [at.name for at in attr.fields(prov_class)]
        init_kwargs = {}
        create_kwargs = {}
        for name, value in kwargs.items():
            if name not in class_attrs:
                create_kwargs[name] = value
            else:
                init_kwargs[name] = value

        obj = self.instantiate(prov_class, *args, **init_kwargs)
        obj.create(**create_kwargs)
        return obj

    def discover(self, discover_cls, cancel=False, start_ip=None, end_ip=None):
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
            # TODO: add support of IPv6
            for idx, octet in enumerate(start_ip.split('.'), start=1):
                key = f'from_ip{idx}'
                form_data.update({key: octet})
        if end_ip:
            end_octet = end_ip.split('.')[-1]
            form_data.update({'to_ip4': end_octet})

        view = navigate_to(self, 'Discover')
        view.fill(form_data)
        if cancel:
            view.cancel.click()
        else:
            view.start.click()

    def wait_for_a_provider(self):
        view = navigate_to(self, 'All')
        logger.info('Waiting for a provider to appear...')
        wait_for(lambda: int(view.entities.paginator.items_amount), fail_condition=0,
                 message="Wait for any provider to appear", num_sec=1000,
                 fail_func=view.browser.refresh)


@navigator.register(InfraProviderCollection, 'All')
@navigator.register(Server, 'InfraProviders')
@navigator.register(InfraProvider, 'All')
class All(CFMENavigateStep):
    VIEW = InfraProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Providers')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.appliance.browser.widgetastic.browser.refresh()
        self.view.toolbar.view_selector.select('Grid View')
        self.view.entities.paginator.reset_selection()


@navigator.register(InfraProviderCollection, 'Add')
@navigator.register(InfraProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = InfraProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Add a New '
                                                                     'Infrastructure Provider')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.configuration.item_select('Add a New '
                                                                     'Infrastructure Provider')


@navigator.register(InfraProviderCollection, 'Discover')
class Discover(CFMENavigateStep):
    VIEW = InfraProvidersDiscoverView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Discover '
                                                                     'Infrastructure Providers')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.configuration.item_select('Discover '
                                                                     'Infrastructure Providers')


@navigator.register(InfraProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = InfraProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()

    def resetter(self, *args, **kwargs):
        """Reset view to Summary View if available"""
        view_selector = self.view.toolbar.view_selector
        if view_selector.is_displayed and view_selector.selected != 'Summary View':
            view_selector.select('Summary View')


@navigator.register(InfraProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=True).ensure_checked()
        try:
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(InfraProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = ProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=True).ensure_checked()
        try:
            self.prerequisite_view.toolbar.configuration.item_select(
                'Edit Selected Infrastructure Providers')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.configuration.item_select(
                'Edit Selected Infrastructure Providers')


@navigator.register(InfraProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = ProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        mon = self.prerequisite_view.toolbar.monitoring
        try:
            mon.item_select('Timelines')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            mon.item_select('Timelines')


@navigator.register(InfraProvider, 'Clusters')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = ProviderClustersView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.entities.summary('Relationships').click_at('Clusters')


@navigator.register(InfraProvider, 'Hosts')
class ProviderHosts(CFMENavigateStep):
    VIEW = ProviderAllHostsView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Relationships').click_at('Hosts')


@navigator.register(InfraProvider, 'ProviderNodes')  # matching other infra class destinations
class ProviderNodes(CFMENavigateStep):
    VIEW = ProviderNodesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.summary('Relationships').click_at(
                self.obj.hosts_menu_item)
        except NameError:
            raise DestinationNotFound(
                "{} aren't present on details page of this provider"
                .format(self.obj.hosts_menu_item))


@navigator.register(InfraProvider, 'ProviderTemplates')
class ProviderTemplates(CFMENavigateStep):
    VIEW = ProviderTemplatesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Relationships').click_at('Templates')


@navigator.register(InfraProvider, 'ProviderVms')
class ProviderVms(CFMENavigateStep):
    VIEW = ProviderVmsView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Relationships').click_at('Virtual Machines')


@navigator.register(InfraProvider, "UtilTrendSummary")
class ProviderOptimizeUtilization(CFMENavigateStep):
    VIEW = ProviderUtilizationTrendsView

    prerequisite = NavigateToAttribute("appliance.collections.utilization", "All")

    def step(self, *args, **kwargs):
        path = [self.appliance.region(), "Providers", self.obj.name]
        if self.appliance.version >= "5.11":
            path.insert(0, "Enterprise")
        self.prerequisite_view.tree.click_path(*path)
