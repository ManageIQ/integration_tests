from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from utils import providers
from cfme.networks.views import SubnetView
from cfme.networks.views import SubnetDetailsView


class SubnetCollection(Navigatable):
    ''' Collection object for Subnet object
        Note: Network providers object are not implemented in mgmt
    '''

    def instantiate(self, name):
        return Subnet(name=name)

    def all(self):
        view = navigate_to(Subnet, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [Subnet(name=s.name) for s in list_networks_obj]


class Subnet(Taggable, Updateable, SummaryMixin, Navigatable):
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_subnet'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ["NetworkSubnet"]

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
    def parent_provider(self):
        ''' Return object of parent cloud provider '''
        view = navigate_to(self, 'Details')
        provider_name = view.contents.relationships.get_text_of('Parent ems cloud')
        provider_obj = providers.get_crud_by_name(provider_name)
        return provider_obj

    @property
    def network_provider(self):
        ''' Return object of network manager '''
        view = navigate_to(self, 'Details')
        provider_name = view.contents.relationships.get_text_of('Network Manager')
        prov_obj = Subnet(name=provider_name)
        return prov_obj

    @property
    def zone(self):
        view = navigate_to(self, 'Details')
        a_zone = view.contents.relationships.get_text_of('Zone')
        return a_zone


@navigator.register(Subnet, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(Subnet, 'Details')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = SubnetDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(Subnet, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = SubnetDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
