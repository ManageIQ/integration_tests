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


details_page = Region(infoblock_type='detail')


class NetworkPort(Taggable, Updateable, SummaryMixin, Navigatable):
    ''' Class representing network ports in sdn '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_port'
    string_name = 'NetworkPort'
    quad_name = None
    db_types = ["CloudNetworkPort"]

    def __init__(
            self, name=None, key=None, zone=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key
        self.zone = zone

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

    def get_mac_address(self):
        ''' Returns mac adress (string) of the port '''
        mac = self.get_detail('Properties','Mac Address')
        return mac

    def get_network_type(self):
        ''' Returns port's type of the network '''
        net_type = self.get_detail('Properties','Type')
        return net_type

    def get_floating_ips(self):
        ''' Returns floating ips (string) of the port '''
        ips = self.get_detail('Properties','Floating ip addresses')
        return ips

    def get_fixed_ips(self):
        ''' Returns fixed ips (string) of the port '''
        ips = self.get_detail('Properties','Fixed ip addresses')
        return ips

    @staticmethod
    def get_all():
        navigate_to(NetworkPort, 'All')
        list_network = [q.name for q in Quadicon.all()]
        return list_network


@navigator.register(NetworkPort, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Ports')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(NetworkPort, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(NetworkPort, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(NetworkPort, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')
