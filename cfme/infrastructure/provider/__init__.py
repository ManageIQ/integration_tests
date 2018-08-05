""" A model of an Infrastructure Provider in CFME
"""
import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import MoveTargetOutOfBoundsException
from widgetastic.utils import Fillable
from widgetastic_patternfly import BreadCrumb

from cfme.base.ui import Server
from cfme.common import TagPageView, Taggable, PolicyProfileAssignable
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider import BaseProvider, provider_types
from cfme.common.provider_views import (
    InfraProviderAddView, InfraProviderEditView, InfraProviderDetailsView, ProviderTimelinesView,
    InfraProvidersDiscoverView, InfraProvidersView, ProviderNodesView, ProviderTemplatesView,
    ProviderVmsView)
from cfme.exceptions import DestinationNotFound
from cfme.infrastructure.cluster import ClusterView, ClusterToolbar
from cfme.infrastructure.host import HostsCollection
from cfme.infrastructure.virtual_machines import InfraVm, InfraTemplate
from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.net import resolve_hostname
from cfme.utils.pretty import Pretty
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import BaseEntitiesView, View, NoSuchElementException


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


@attr.s(hash=False)
class InfraProvider(Pretty, Fillable, BaseProvider, PolicyProfileAssignable, Taggable):
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
    detail_page_suffix = 'provider'
    edit_page_suffix = 'provider_edit'
    refresh_text = "Refresh Relationships and Power States"

    name = attr.ib(default=None)
    key = attr.ib(default=None)
    zone = attr.ib(default=None)
    # hostname = attr.ib(default=None) # defined in CloudInfraProvider class
    # ip_address = attr.ib(default=None) # defined in CloudInfraProvider class
    start_ip = attr.ib(default=None)
    end_ip = attr.ib(default=None)
    provider_data = attr.ib(default=None)

    _collections = {'hosts': HostsCollection}

    def __attrs_post_init__(self):
        super(InfraProvider, self).__attrs_post_init__()
        self.parent = self.appliance.collections.infra_providers

    @property
    def hostname(self):
        return getattr(self.default_endpoint, "hostname", None)

    @hostname.setter
    def hostname(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.hostname = value
        else:
            logger.warn("can't set hostname because default endpoint is absent")

    @property
    def ip_address(self):
        return getattr(self.default_endpoint, "ipaddress", resolve_hostname(str(self.hostname)))

    @ip_address.setter
    def ip_address(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.ipaddress = value
        else:
            logger.warn("can't set ipaddress because default endpoint is absent")

    @variable(alias="db")
    def num_template(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        vms = self.appliance.db.client["vms"]
        temlist = list(self.appliance.db.client.session.query(vms.name)
                       .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name)
                       .filter(vms.template == True))  # NOQA
        return len(temlist)

    @num_template.variant('ui')
    def num_template_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of(self.template_name))

    @variable(alias="db")
    def num_vm(self):
        """ Returns the providers number of instances, as shown on the Details page."""
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        vms = self.appliance.db.client["vms"]
        vmlist = list(self.appliance.db.client.session.query(vms.name)
                      .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                      .filter(ext_management_systems.name == self.name)
                      .filter(vms.template == False))  # NOQA
        return len(vmlist)

    @num_vm.variant('ui')
    def num_vm_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of(self.vm_name))

    def load_all_provider_instances(self):
        return self.load_all_provider_vms()

    def load_all_provider_vms(self):
        """ Loads the list of instances that are running under the provider.

        """
        view = navigate_to(self, 'Details')
        if view.entities.summary("Relationships").get_text_of(self.vm_name) == "0":
            return False
        else:
            view.entities.summary("Relationships").click_at(self.vm_name)
            return True

    def load_all_provider_images(self):
        self.load_all_provider_templates()

    def load_all_provider_templates(self):
        """ Loads the list of images that are available under the provider.

        """
        # todo: replace these methods with new nav location
        view = navigate_to(self, 'Details')
        if view.entities.summary("Relationships").get_text_of(self.template_name) == "0":
            return False
        else:
            view.entities.summary("Relationships").click_at(self.template_name)
            return True

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
            host.update_credentials_rest(credentials=host_data['credentials'])

    def remove_hosts_credentials(self):
        for host in self.hosts.all():
            host.remove_credentials_rest()


# todo: update all docstrings
@attr.s
class InfraProviderCollection(BaseCollection):
    """Collection object for InfraProvider object
    """

    ENTITY = InfraProvider

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

    def instantiate(self, prov_class, *args, **kwargs):
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
                key = 'from_ip{idx}'.format(idx=idx)
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

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        self.appliance.browser.widgetastic.browser.refresh()
        tb = self.view.toolbar
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        self.view.entities.paginator.reset_selection()


@navigator.register(InfraProviderCollection, 'Add')
@navigator.register(InfraProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = InfraProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
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

    def step(self):
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

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()

    def resetter(self):
        """Reset view and selection"""
        view_selector = self.view.toolbar.view_selector
        if view_selector.selected != 'Summary View':
            view_selector.select('Summary View')


@navigator.register(InfraProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        try:
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(InfraProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = InfraProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
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

    def step(self):
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

    def step(self):
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

    def step(self):
        self.prerequisite_view.entities.summary('Relationships').click_at('Templates')


@navigator.register(InfraProvider, 'ProviderVms')
class ProviderVms(CFMENavigateStep):
    VIEW = ProviderVmsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.summary('Relationships').click_at('Virtual Machines')
