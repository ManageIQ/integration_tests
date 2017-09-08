from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import SubnetDetailsView, SubnetView
from utils import providers, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class SubnetCollection(Navigatable):
    """ Collection object for Subnet object
        Note: Network providers object are not implemented in mgmt
    """
    def __init__(self, appliance=None, parent_provider=None):
        Navigatable.__init__(self, appliance=appliance)
        self.parent = parent_provider

    def instantiate(self, name):
        return Subnet(name=name, appliance=self.appliance, collection=self)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'CloudSubnets')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all()
        return [self.instantiate(name=p.name) for p in list_networks_obj]


class Subnet(WidgetasticTaggable, Navigatable):
    """Class representing subnets in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'network_subnet'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ['NetworkSubnet']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        self.collection = collection or SubnetCollection(appliance=appliance)
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
        """ Returns network provider """
        from cfme.networks.provider import NetworkProviderCollection
        # subnet collection contains reference to provider
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

    @property
    def zone(self):
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Zone')


@navigator.register(SubnetCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')


@navigator.register(Subnet, 'Details')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = SubnetDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(Subnet, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = SubnetDetailsView

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
