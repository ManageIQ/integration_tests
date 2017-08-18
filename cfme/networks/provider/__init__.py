from utils import version
from cfme.common.provider import BaseProvider
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.wait import wait_for
from cfme.networks.views import NetworkProviderView
from cfme.networks.views import NetworkProviderDetailsView
from cfme.networks.balancer import BalancerCollection
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.subnet import SubnetCollection
from cfme.networks.security_group import SecurityGroupCollection


class NetworkProviderCollection(Navigatable):
    ''' Collection object for NetworkProvider object
        Note: Network providers object are not implemented in mgmt
    '''
    def __init__(self, appliance=None):
        self.appliance = appliance

    def instantiate(self, name):
        return NetworkProvider(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(NetworkProvider, 'All')
        list_networks = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=p.name) for p in list_networks]

    @property
    def balancers(self):
        return BalancerCollection(parent_provider=self)

    @property
    def subnets(self):
        return SubnetCollection(parent_provider=self)

    @property
    def networks(self):
        return CloudNetworkCollection(parent_provider=self)

    @property
    def ports(self):
        return NetworkPortCollection(parent_provider=self)

    @property
    def routers(self):
        return NetworkRouterCollection(parent_provider=self)

    @property
    def security_groups(self):
        return SecurityGroupCollection(parent_provider=self)


class NetworkProvider(BaseProvider):
    ''' Class representing network provider in sdn
        Note: Network provider can be added to cfme database
              only automaticaly with cloud provider
    '''
    STATS_TO_MATCH = []
    string_name = 'Networks'
    in_version = ('5.8', version.LATEST)
    page_name = 'networks'
    edit_page_suffix = ''
    detail_page_suffix = ''
    refresh_text = 'Refresh items and relationships'
    quad_name = None
    category = 'networks'
    provider_types = {}
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    db_types = ['NetworksManager']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        if collection is None:
            collection = NetworkProviderCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
        self.name = name
        self.provider = provider

    def refresh_provider_relationships(self, cancel=True):
        ''' Refresh relationships of network provider '''
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Refresh Relationships and Power States',
                                               handle_alert=not cancel)

    def delete(self, cancel=True):
        ''' Deltes a network provider from CFME '''
        view = navigate_to(self, 'Details')
        wait_for(lambda: view.toolbar.configuration.item_enabled('Remove this Network Provider'),
                 num_sec=10)
        view.toolbar.configuration.item_select('Remove this Network Provider',
                                               handle_alert=not cancel)

    @property
    def valid_credentials_state(self):
        ''' Checks whether credentials are valid '''
        view = navigate_to(self, 'Details')
        cred_state = view.contents.status.get_text_of('Default Credentials')
        return cred_state == "Valid"

    @property
    def exists(self):
        view = navigate_to(self, 'Details')
        return view.is_displayed


@navigator.register(NetworkProvider, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkProviderView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Providers')


@navigator.register(NetworkProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = NetworkProviderDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(NetworkProvider, 'CloudSubnets')
class OpenCloudSubnets(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Subnets')


@navigator.register(NetworkProvider, 'CloudNetworks')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Networks')


@navigator.register(NetworkProvider, 'NetworkRouters')
class OpenNetworkRouters(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Routers')


@navigator.register(NetworkProvider, 'SecurityGroups')
class OpenSecurityGroups(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Security Groups')


@navigator.register(NetworkProvider, 'FloatingIPs')
class OpenFloatingIPs(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Floating IPs')


@navigator.register(NetworkProvider, 'NetworkPorts')
class OpenNetworkPorts(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Network Ports')


@navigator.register(NetworkProvider, 'LoadBalancers')
class OpenNetworkBalancers(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Load Balancers')


@navigator.register(NetworkProvider, 'TopologyFromDetails')
class OpenTopologyFromDetails(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.overview.click_at('Topology')


@navigator.register(NetworkProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkProviderDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
