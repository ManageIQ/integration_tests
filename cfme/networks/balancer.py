from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.networks.views import BalancerDetailsView
from cfme.networks.views import BalancerView
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class BalancerCollection(Navigatable):
    """Collection object for Balancer object"""
    def __init__(self, appliance=None, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return Balancer(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(Balancer, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=b.name) for b in list_networks_obj]


class Balancer(WidgetasticTaggable, Navigatable):
    """Class representing balancers in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'network_balancer'
    string_name = 'NetworkBalancer'
    refresh_text = 'Refresh items and relationships'
    detail_page_suffix = 'network_balancer_detail'
    quad_name = None
    db_types = ['NetworkBalancer']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        if collection is None:
            collection = BalancerCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
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


@navigator.register(Balancer, 'All')
class All(CFMENavigateStep):
    VIEW = BalancerView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Load Balancers')


@navigator.register(Balancer, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = BalancerDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(Balancer, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = BalancerDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
