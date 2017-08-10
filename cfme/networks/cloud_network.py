from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.web_ui import (
    Region, InfoBlock, Quadicon, toolbar as tb, paginator
)
from cfme.fixtures import pytest_selenium as sel
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from utils import providers
from cfme.networks.provider import NetworkProvider
from cfme.web_ui import Quadicon


details_page = Region(infoblock_type='detail')


class CloudNetwork(Taggable, Updateable, SummaryMixin, Navigatable):
    ''' Class representing cloud networks in cfme database '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'cloud_network'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ["CloudNetworks"]

    def __init__(
            self, name=None, key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key

    def load_details(self):
        ''' Load details page via navigation '''
        navigate_to(self, 'Details')

    def get_detail(self, *ident):
        ''' Gets details from the details infoblock
        The function first ensures that we are on the detail page for the specific provider.
        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        '''
        self.load_details()
        return details_page.infoblock.text(*ident)

    def get_parent_provider(self):
        ''' Return object of parent cloud provider '''
        provider_name = self.get_detail('Relationships','Parent ems cloud')
        provider = providers.get_crud_by_name(provider_name)
        return provider

    def get_network_provider(self):
        ''' Return object of network manager '''
        manager_name = self.get_detail('Relationships','Network Manager')
        prov_obj = NetworkProvider(name=manager_name)
        return prov_obj

    def get_network_type(self):
        ''' Return type of network '''
        return self.get_detail('Properties','Type')

    @staticmethod
    def get_all():
        ''' Get list of all cloud networks in cfme database '''
        navigate_to(CloudNetwork, 'All')
        list_network = [q.name for q in Quadicon.all()]
        return list_network


@navigator.register(CloudNetwork, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Networks')

    def resetter(self):
        tb.select("Grid View")
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(CloudNetwork, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(CloudNetwork, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(CloudNetwork, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')
