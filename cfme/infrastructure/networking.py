import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import PaginationPane, ItemsToolBarViewSelector, Text


class InfraNetworking(BaseEntity):
    _param_name = 'InfraNetworking'


@attr.s
class InfraNetworkingCollection(BaseCollection):
    """Collection object for the :py:class:`cmfe.infrastructure.networking.InfraNetworking`."""
    ENTITY = InfraNetworking


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


@navigator.register(InfraNetworkingCollection)
class All(CFMENavigateStep):
    VIEW = InfraNetworkingAllView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Networking')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.view.toolbar.view_selector.select('Grid View')
