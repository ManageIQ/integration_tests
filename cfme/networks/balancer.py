from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from cfme.networks.views import BalancerView
from cfme.networks.views import BalancerDetailsView


class BalancerCollection(Navigatable):
    ''' Collection object for Balancer object
    '''

    def instantiate(self, name):
        return Balancer(name=name)

    def all(self):
        view = navigate_to(Balancer, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [Balancer(name=b.name) for b in list_networks_obj]


class Balancer(Taggable, Updateable, SummaryMixin, Navigatable):
    ''' Class representing balancers in sdn '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_balancer'
    string_name = 'NetworkBalancer'
    refresh_text = "Refresh items and relationships"
    detail_page_suffix = 'network_balancer_detail'
    quad_name = None
    db_types = ["NetworkBalancer"]

    def __init__(
            self, name, provider=None):
        if provider:
            self.appliance = provider.appliance
        else:
            self.appliance = None
        Navigatable.__init__(self, appliance=self.appliance)
        self.name = name
        self.provider = provider

    @property
    def health_checks(self):
        ''' Returns health check state '''
        view = navigate_to(self, 'Details')
        checks = view.contents.properties.get_text_of('Health checks')
        return checks

    @property
    def listeners(self):
        ''' Returns listeners of balancer '''
        view = navigate_to(self, 'Details')
        listener = view.contents.properties.get_text_of('Listeners')
        return listener


@navigator.register(Balancer, 'All')
class All(CFMENavigateStep):
    VIEW = BalancerView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Load Balancers')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


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
