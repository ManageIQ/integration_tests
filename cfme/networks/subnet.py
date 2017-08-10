from utils import version
from cfme.common.provider import BaseProvider
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.appliance import current_appliance
from cfme.web_ui import (
    Region, Form, AngularSelect, InfoBlock, Input, Quadicon,
    form_buttons, toolbar as tb, paginator, fill, FileInput,
    CFMECheckbox, Select, flash, tabstrip
)
from cfme.fixtures import pytest_selenium as sel
from cfme.base.login import BaseLoggedInPage
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import PolicyProfileAssignable, Taggable, SummaryMixin


details_page = Region(infoblock_type='detail')


class Subnet(Taggable, Updateable, SummaryMixin, Navigatable):
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'network_subnet'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ["NetworkSubnet"]

    def __init__(
            self, name=None, key=None, zone=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key
        self.zone = zone

    def load_details(self):
        """Load details page via navigation"""
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

    def get_zone(self):
        a_zone = self.get_detail('Relationships','Zone')
        return a_zone

    @staticmethod
    def get_all():
        navigate_to(Subnet, 'All')
        list_subnets = [q.name for q in Quadicon.all()]
        return list_subnets


@navigator.register(Subnet, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(Subnet, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(Subnet, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(Subnet, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')
