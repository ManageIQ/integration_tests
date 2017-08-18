from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from utils import providers
from cfme.networks.views import CloudNetworkView
from cfme.networks.views import CloudNetworkDetailsView


class CloudNetworkCollection(Navigatable):
    ''' Collection object for Cloud Network object '''
    def __init__(self, appliance=None, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return CloudNetwork(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(CloudNetwork, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=n.name) for n in list_networks_obj]


class CloudNetwork(Taggable, Updateable, SummaryMixin, Navigatable):
    ''' Class representing cloud networks in cfme database '''
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'cloud_network'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ['CloudNetwork']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        if collection is None:
            collection = CloudNetworkCollection(appliance=appliance)
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
        ''' Return object of network manager '''
        view = navigate_to(self, 'Details')
        provider_name = view.contents.relationships.get_text_of('Network Manager')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_type(self):
        ''' Return type of network '''
        view = navigate_to(self, 'Details')
        return view.contents.properties.get_text_of('Type')


@navigator.register(CloudNetwork, 'All')
class All(CFMENavigateStep):
    VIEW = CloudNetworkView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Networks')


@navigator.register(CloudNetwork, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = CloudNetworkDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(CloudNetwork, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = CloudNetworkDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
