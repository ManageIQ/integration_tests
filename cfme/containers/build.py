import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search


class BuildToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class BuildView(BaseLoggedInPage):
    search = View.nested(Search)
    toolbar = View.nested(BuildToolbar)

    @property
    def in_build(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Containers', 'Container Builds'])


class BuildDefaultView(BuildView):
    title = Text(".//div[@id='main-content']//h1")

    @property
    def is_displayed(self):
        return (
            self.in_build and
            self.title.text == 'Container Builds'
        )

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


@attr.s
class Build(BaseEntity):
    pass


@attr.s
class BuildCollection(BaseCollection):
    ENTITY = Build


@navigator.register(BuildCollection, 'All')
class All(CFMENavigateStep):
    VIEW = BuildDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Builds')
