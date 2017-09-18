from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import Accordion, ManageIQTree
from widgetastic_patternfly import Dropdown, FlashMessages

from cfme.base.login import BaseLoggedInPage
from cfme.base import Server
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ServicesCatalogView(BaseLoggedInPage):

    @property
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'Catalogs'])

    @property
    def is_displayed(self):
        return self.in_explorer and self.configuration.is_displayed and not self.catalogs.is_dimmed

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

    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    flash = FlashMessages(".//div[@id='flash_msg_div']/div")


@navigator.register(Server)
class ServicesCatalog(CFMENavigateStep):
    VIEW = ServicesCatalogView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Services", "Catalogs")
