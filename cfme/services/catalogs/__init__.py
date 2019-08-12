from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree


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

    # TODO(nansari/sshveta): For backward compatibility. It is difficult to figure out where those
    #  are used
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
