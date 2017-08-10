from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.web_ui import (
    Region, Quadicon, toolbar as tb, paginator
)
from cfme.fixtures import pytest_selenium as sel
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from functools import partial


pol_btn = partial(tb.select, 'Policy')
details_page = Region(infoblock_type='detail')


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
            self, name=None, key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key

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

    def get_health_checks(self):
        ''' Returns health check state '''
        checks = self.get_detail('Properties', 'Health checks')
        return checks

    def get_listeners(self):
        ''' Returns listeners of balancer '''
        listener = self.get_detail('Properties', 'Listeners')
        return listener

    @staticmethod
    def get_all():
        ''' Get list of all balancers in cfme database '''
        navigate_to(Balancer, 'All')
        list_balancers = [q.name for q in Quadicon.all()]
        return list_balancers


@navigator.register(Balancer, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Load Balancers')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(Balancer, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(Balancer, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(Balancer, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')
