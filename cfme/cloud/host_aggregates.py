import attr

from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import BootstrapNav, Dropdown
from widgetastic_manageiq import Accordion, ManageIQTree, Search, ItemsToolBarViewSelector

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class HostAggregatesToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostAggregatesView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    search = View.nested(Search)
    toolbar = View.nested(HostAggregatesToolbar)

    @property
    def in_host_aggregates(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Host Aggregates'])

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class HostAggregatesDefaultView(HostAggregatesView):
    title = Text('//div[@id="main-content"]//h1')

    @property
    def is_displayed(self):
        return self.in_host_aggregates and self.title.is_displayed


@attr.s
class HostAggregates(BaseEntity):
    pass


@attr.s
class HostAggregatesCollection(BaseCollection):
    ENTITY = HostAggregates


@navigator.register(HostAggregatesCollection, 'All')
class All(CFMENavigateStep):
    VIEW = HostAggregatesDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Host Aggregates')
