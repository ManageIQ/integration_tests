from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.networks.views import CloudNetworkDetailsView, CloudNetworkView
from utils import providers, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class CloudNetworkCollection(Navigatable):
    """Collection object for Cloud Network object"""
    def __init__(self, appliance=None, parent_provider=None):
        Navigatable.__init__(self, appliance=appliance)
        self.parent = parent_provider

    def instantiate(self, name):
        return CloudNetwork(name=name, appliance=self.appliance, collection=self)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'CloudNetworks')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=n.name) for n in list_networks_obj]


class CloudNetwork(WidgetasticTaggable, Navigatable):
    """Class representing cloud networks in cfme database"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'cloud_network'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ['CloudNetwork']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        self.collection = collection or CloudNetworkCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.name = name
        self.provider = provider

    @property
    def parent_provider(self):
        """ Return object of parent cloud provider """
        view = navigate_to(self, 'Details')
        provider_name = view.entities.relationships.get_text_of('Parent ems cloud')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_provider(self):
        """ Return object of network manager """
        view = navigate_to(self, 'Details')
        provider_name = view.entities.relationships.get_text_of('Network Manager')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_type(self):
        """ Return type of network """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')


@navigator.register(CloudNetworkCollection, 'All')
class All(CFMENavigateStep):
    VIEW = CloudNetworkView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Networks')


@navigator.register(CloudNetwork, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('collection', 'All')
    VIEW = CloudNetworkDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(CloudNetwork, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
