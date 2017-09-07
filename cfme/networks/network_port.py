from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import NetworkPortDetailsView, NetworkPortView
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class NetworkPortCollection(Navigatable):
    """ Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    """
    def __init__(self, appliance=None, parent_provider=None):
        Navigatable.__init__(self, appliance=appliance)
        self.parent = parent_provider

    def instantiate(self, name):
        return NetworkPort(name=name, appliance=self.appliance, collection=self)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'NetworkPorts')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=p.name) for p in list_networks_obj]


class NetworkPort(WidgetasticTaggable, Navigatable):
    """Class representing network ports in sdn"""
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_port'
    string_name = 'NetworkPort'
    quad_name = None
    db_types = ['CloudNetworkPort']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        self.collection = collection or NetworkPortCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.name = name
        self.provider = provider

    @property
    def mac_address(self):
        """ Returns mac adress (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Mac address')

    @property
    def network_type(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')

    @property
    def floating_ips(self):
        """ Returns floating ips (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Floating ip addresses')

    @property
    def fixed_ips(self):
        """ Returns fixed ips (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Fixed ip addresses')

    @property
    def network_provider(self):
        """ Returns network provider """
        from cfme.networks.provider import NetworkProviderCollection
        # port collection contains reference to provider
        if self.collection.parent:
            return self.collection.parent
        # otherwise get provider name from ui
        view = navigate_to(self, 'Details')
        try:
            prov_name = view.entities.relationships.get_text_of("Network Manager")
            collection = NetworkProviderCollection(appliance=self.appliance)
            return collection.instantiate(name=prov_name)
        except ItemNotFound:  # BZ 1480577
            return None


@navigator.register(NetworkPortCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkPortView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Ports')


@navigator.register(NetworkPort, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('collection', 'All')
    VIEW = NetworkPortDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(NetworkPort, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
