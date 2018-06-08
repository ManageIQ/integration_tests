from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import Search, ItemsToolBarViewSelector


class HostAggregatesToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostAggregatesView(BaseLoggedInPage):
    search = View.nested(Search)
    toolbar = View.nested(HostAggregatesToolbar)

    @property
    def in_host_aggregates(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Host Aggregates'])


class HostAggregatesDefaultView(HostAggregatesView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_host_aggregates and
            self.title.text == 'Host Aggregates'
        )


class HostAggregates(Navigatable):
    pass


@navigator.register(HostAggregates, 'All')
class All(CFMENavigateStep):
    VIEW = HostAggregatesDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Host Aggregates')
        self.view.search.clear_simple_search()
