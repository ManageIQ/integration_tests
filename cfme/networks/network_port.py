from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.networks.views import NetworkPortDetailsView
from cfme.networks.views import NetworkPortView
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class NetworkPortCollection(Navigatable):
    """ Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    """
    def __init__(self, appliance=None, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return NetworkPort(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(NetworkPort, 'All')
        list_networks_obj = view.entities.get_all()
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
        if collection is None:
            collection = NetworkPortCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
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


@navigator.register(NetworkPort, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkPortView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Ports')


@navigator.register(NetworkPort, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = NetworkPortDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(NetworkPort, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkPortDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
