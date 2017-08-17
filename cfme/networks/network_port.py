from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from cfme.networks.views import NetworkPortView
from cfme.networks.views import NetworkPortDetailsView


class NetworkPortCollection(Navigatable):
    ''' Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    '''

    def instantiate(self, name):
        return NetworkPort(name=name)

    def all(self):
        view = navigate_to(NetworkPort, 'All')
        list_networks_obj = view.entities.get_all()
        return [NetworkPort(name=p.name) for p in list_networks_obj]


class NetworkPort(Taggable, Updateable, SummaryMixin, Navigatable):
    ''' Class representing network ports in sdn '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_port'
    string_name = 'NetworkPort'
    quad_name = None
    db_types = ["CloudNetworkPort"]

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
    def mac_address(self):
        ''' Returns mac adress (string) of the port '''
        view = navigate_to(self, 'Details')
        mac = view.contents.properties.get_text_of('Mac address')
        return mac

    @property
    def network_type(self):
        view = navigate_to(self, 'Details')
        net_type = view.contents.properties.get_text_of('Type')
        return net_type

    @property
    def floating_ips(self):
        ''' Returns floating ips (string) of the port '''
        view = navigate_to(self, 'Details')
        ips = view.contents.properties.get_text_of('Floating ip addresses')
        return ips

    @property
    def fixed_ips(self):
        ''' Returns fixed ips (string) of the port '''
        view = navigate_to(self, 'Details')
        ips = view.contents.properties.get_text_of('Fixed ip addresses')
        return ips


@navigator.register(NetworkPort, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkPortView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Ports')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(NetworkPort, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = NetworkPortDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(NetworkPort, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkPortDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
