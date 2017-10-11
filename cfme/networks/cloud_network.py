from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import CloudNetworkDetailsView, CloudNetworkView
from cfme.utils import providers, version
from cfme.utils.appliance import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class CloudNetworkCollection(BaseCollection):
    """Collection object for Cloud Network object"""
    def __init__(self, appliance, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return CloudNetwork(collection=self, name=name)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'CloudNetworks')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=n.name) for n in list_networks_obj]


class CloudNetwork(WidgetasticTaggable, BaseEntity):
    """Class representing cloud networks in cfme database"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'cloud_network'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ['CloudNetwork']

    def __init__(self, collection, name, provider=None):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.name = name
        self.provider = provider

    @property
    def parent_provider(self):
        """ Return object of parent cloud provider """
        view = navigate_to(self, 'Details')
        provider_name = view.entities.relationships.get_text_of('Parent ems cloud')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_type(self):
        """ Return type of network """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')

    @property
    def network_provider(self):
        """ Returns network provider """
        from cfme.networks.provider import NetworkProviderCollection
        # cloud network collection contains reference to provider
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
