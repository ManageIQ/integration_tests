from navmazing import NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import PaginationPane, ItemsToolBarViewSelector, Text


class InfraNetworking(Navigatable):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


class InfraNetworkingView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""

    @property
    def in_infra_networking(self):
        nav_chain = ['Compute', 'Infrastructure', 'Networking']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class InfraNetworkingToolbar(View):
    """The toolbar on the main page"""
    policy = Dropdown('Policy')

    view_selector = View.nested(ItemsToolBarViewSelector)


class InfraNetworkingEntities(View):
    """Entities on the main page"""
    title = Text('//div[@id="main-content"]//h1')


class InfraNetworkingAllView(InfraNetworkingView):
    """The "all" view -- a list"""
    @property
    def is_displayed(self):
        return (
            self.in_infra_networking and
            self.entities.title.text == 'All Switches')

    toolbar = View.nested(InfraNetworkingToolbar)
    entities = View.nested(InfraNetworkingEntities)
    paginator = PaginationPane()


@navigator.register(InfraNetworking, 'All')
class All(CFMENavigateStep):
    VIEW = InfraNetworkingAllView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Networking')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select('Grid View')
