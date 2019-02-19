from navmazing import NavigateToSibling
from widgetastic_patternfly import Dropdown
from widgetastic.widget import View, Text

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import Accordion, ItemsToolBarViewSelector, ManageIQTree


class ServicesCatalogView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @property
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'Catalogs'])

    @property
    def is_displayed(self):
        return self.in_explorer

    @View.nested
    class service_catalogs(Accordion):  # noqa
        ACCORDION_NAME = "Service Catalogs"

        tree = ManageIQTree()

    @View.nested
    class catalog_items(Accordion):  # noqa
        ACCORDION_NAME = "Catalog Items"

        tree = ManageIQTree()

    @View.nested
    class orchestration_templates(Accordion):  # noqa
        ACCORDION_NAME = "Orchestration Templates"

        tree = ManageIQTree()

    @View.nested
    class catalogs(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class toolbar(View):  # noqa
        configuration = Dropdown('Configuration')
        policy = Dropdown('Policy')
        view_selector = View.nested(ItemsToolBarViewSelector)

    # for backward compatibility. it is difficult to figure out where those are used
    # TODO: this should be fixed by this code owner
    @property
    def configuration(self):
        return self.toolbar.configuration

    @property
    def policy(self):
        return self.toolbar.policy


@navigator.register(Server)
class ServicesCatalog(CFMENavigateStep):
    VIEW = ServicesCatalogView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self, *args, **kwargs):
        self.view.navigation.select("Services", "Catalogs")
