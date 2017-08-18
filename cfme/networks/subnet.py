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
    def __init__(self, appliance=None, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return Subnet(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(Subnet, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]


class Subnet(Taggable, Updateable, SummaryMixin, Navigatable):
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'network_subnet'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ['NetworkSubnet']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        if collection is None:
            collection = SubnetCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
        self.name = name
        self.provider = provider

    @property
    def parent_provider(self):
        ''' Return object of parent cloud provider '''
        view = navigate_to(self, 'Details')
        provider_name = view.contents.relationships.get_text_of('Parent ems cloud')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_provider(self):
        ''' Return name of network manager '''
        view = navigate_to(self, 'Details')
        return view.contents.relationships.get_text_of('Network Manager')

    @property
    def zone(self):
        view = navigate_to(self, 'Details')
        return view.contents.relationships.get_text_of('Zone')


@navigator.register(Subnet, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')


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
