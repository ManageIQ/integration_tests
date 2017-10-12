import attr

from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import BalancerDetailsView, BalancerView
from cfme.utils import version
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
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

    name = attr.ib()

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

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
        # security group collection contains reference to provider
        if self.provider:
            return self.provider
        # otherwise get provider name from ui
        view = navigate_to(self, 'Details')
        try:
            prov_name = view.entities.relationships.get_text_of("Network Manager")
            collection = self.appliance.collections.network_provider
            return collection.instantiate(name=prov_name)
        except ItemNotFound:  # BZ 1480577
            return None


@attr.s
class BalancerCollection(BaseCollection):
    """Collection object for Balancer object"""

    ENTITY = Balancer

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'LoadBalancers')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=b.name) for b in list_networks_obj]


@navigator.register(BalancerCollection, 'All')
class All(CFMENavigateStep):
    VIEW = BalancerView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Load Balancers')


@navigator.register(Balancer, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = BalancerDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
