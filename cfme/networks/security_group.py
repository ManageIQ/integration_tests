from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import SecurityGroupDetailsView, SecurityGroupView
from cfme.utils import version
from cfme.utils.appliance import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class SecurityGroupCollection(BaseCollection):
    """ Collection object for SecurityGroup object
        Note: Network providers object are not implemented in mgmt
    """
    def __init__(self, appliance, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return SecurityGroup(collection=self, name=name)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'SecurityGroups')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]


class SecurityGroup(WidgetasticTaggable, BaseEntity):
    """Class representing security group in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'security_group'
    string_name = 'SecurityGroup'
    quad_name = None
    db_types = ['SecurityGroup']

    def __init__(self, collection, name, provider=None):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.name = name
        self.provider = provider

    @property
    def network_provider(self):
        """ Returns network provider """
        from cfme.networks.provider import NetworkProviderCollection
        # security group collection contains reference to provider
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


@navigator.register(SecurityGroupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('collection', 'All')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
