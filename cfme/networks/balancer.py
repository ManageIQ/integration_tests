from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import BalancerDetailsView, BalancerView
from cfme.utils import version
from cfme.utils.appliance import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class BalancerCollection(BaseCollection):
    """Collection object for Balancer object"""
    def __init__(self, appliance, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return Balancer(collection=self, name=name)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'LoadBalancers')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=b.name) for b in list_networks_obj]


class Balancer(WidgetasticTaggable, BaseEntity):
    """Class representing balancers in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'network_balancer'
    string_name = 'NetworkBalancer'
    refresh_text = 'Refresh items and relationships'
    detail_page_suffix = 'network_balancer_detail'
    quad_name = None
    db_types = ['NetworkBalancer']

    def __init__(self, collection, name, provider=None):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.name = name
        self.provider = provider

    @property
    def health_checks(self):
        """ Returns health check state """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Health checks')

    @property
    def listeners(self):
        """ Returns listeners of balancer """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Listeners')

    @property
    def network_provider(self):
        """ Returns network provider """
        from cfme.networks.provider import NetworkProviderCollection
        # balancer collection contains reference to provider
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


@navigator.register(BalancerCollection, 'All')
class All(CFMENavigateStep):
    VIEW = BalancerView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Load Balancers')


@navigator.register(Balancer, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('collection', 'All')
    VIEW = BalancerDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
