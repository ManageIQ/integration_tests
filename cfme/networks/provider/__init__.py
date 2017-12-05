import attr
from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.common.provider import BaseProvider
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.networks.balancer import BalancerCollection
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.security_group import SecurityGroupCollection
from cfme.networks.subnet import SubnetCollection
from cfme.networks.views import (
    NetworkProviderDetailsView,
    NetworkProviderView,
    NetworkProviderAddView,
    OneProviderBalancerView,
    OneProviderCloudNetworkView,
    OneProviderNetworkPortView,
    OneProviderNetworkRouterView,
    OneProviderSecurityGroupView,
    OneProviderSubnetView
)
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
class NetworkProvider(BaseProvider, WidgetasticTaggable, BaseEntity):
    """ Class representing network provider in sdn

    Note: Network provider can be added to cfme database
          only automaticaly with cloud provider
    """
    STATS_TO_MATCH = []
    string_name = 'Network'
    in_version = ('5.8', version.LATEST)
    edit_page_suffix = ''
    refresh_text = 'Refresh Relationships and Power States'
    quad_name = None
    category = 'networks'
    provider_types = {}
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    db_types = ['NetworksManager']

    _collections = {
        'balancers': BalancerCollection,
        'cloud_networks': CloudNetworkCollection,
        'ports': NetworkPortCollection,
        'routers': NetworkRouterCollection,
        'subnets': SubnetCollection,
        'security_groups': SecurityGroupCollection,
    }

    name = attr.ib()
    provider = attr.ib(default=None)

    @property
    def valid_credentials_state(self):
        """ Checks whether credentials are valid """
        view = navigate_to(self, 'Details')
        cred_state = view.entities.status.get_text_of('Default Credentials')
        return cred_state == "Valid"

    @cached_property
    def balancers(self):
        return self.collections.balancers

    @cached_property
    def subnets(self):
        return self.collections.subnets

    @cached_property
    def networks(self):
        return self.collections.cloud_networks

    @cached_property
    def ports(self):
        return self.collections.ports

    @cached_property
    def routers(self):
        return self.collections.routers

    @cached_property
    def security_groups(self):
        return self.collections.security_groups


@attr.s
class NetworkProviderCollection(BaseCollection):
    """Collection object for NetworkProvider object
       Note: Network providers object are not implemented in mgmt
    """

    ENTITY = NetworkProvider

    def all(self):
        view = navigate_to(self, 'All')
        list_networks = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=p.name) for p in list_networks]

    # A rare collection override of instantiate
    def instantiate(self, prov_class, *args, **kwargs):
        return prov_class.from_collection(self, *args, **kwargs)

    def create(self, prov_class, *args, **kwargs):
        obj = self.instantiate(prov_class, *args, **kwargs)
        obj.create()


@navigator.register(NetworkProvider, 'All')  # To be removed once all CEMv3
@navigator.register(NetworkProviderCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkProviderView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Providers')


@navigator.register(NetworkProvider, 'Add')  # To be removed once all CEMv3
@navigator.register(NetworkProviderCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = NetworkProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New '
                                                                 'Network Provider')


@navigator.register(NetworkProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = NetworkProviderDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name).click()


@navigator.register(NetworkProvider, 'CloudSubnets')
class OpenCloudSubnets(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderSubnetView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Cloud Subnets')


@navigator.register(NetworkProvider, 'CloudNetworks')
class OpenCloudNetworks(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderCloudNetworkView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Cloud Networks')


@navigator.register(NetworkProvider, 'NetworkRouters')
class OpenNetworkRouters(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderNetworkRouterView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Network Routers')


@navigator.register(NetworkProvider, 'SecurityGroups')
class OpenSecurityGroups(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderSecurityGroupView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Security Groups')


@navigator.register(NetworkProvider, 'FloatingIPs')
class OpenFloatingIPs(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Floating IPs')


@navigator.register(NetworkProvider, 'NetworkPorts')
class OpenNetworkPorts(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderNetworkPortView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Network Ports')


@navigator.register(NetworkProvider, 'LoadBalancers')
class OpenNetworkBalancers(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderBalancerView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Load Balancers')


@navigator.register(NetworkProvider, 'TopologyFromDetails')
class OpenTopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.overview.click_at('Topology')
