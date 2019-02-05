import attr

from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import BootstrapNav, Dropdown
from widgetastic_manageiq import Accordion, ManageIQTree, Search, ItemsToolBarViewSelector

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


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
