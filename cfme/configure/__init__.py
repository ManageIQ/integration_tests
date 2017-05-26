from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import Accordion, ManageIQTree
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.base import Server
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ConfigurationView(BaseLoggedInPage):
    def in_configuration(self):
        return self.logged_in_as_current_user

    @property
    def is_displayed(self):
        return self.in_explorer and not self.access_control.is_dimmed

    @View.nested
    class access_control(Accordion):        # noqa
        ACCORDION_NAME = "Access Control"

        tree = ManageIQTree()

    @View.nested
    class server_settings(Accordion):      # noqa
        ACCORDION_NAME = "Settings"

        tree = ManageIQTree()

    @View.nested
    class diagnostics(Accordion):       # noqa
        ACCORDION_NAME = "Diagnostics"

        tree = ManageIQTree()

    @View.nested
    class database(Accordion):      # noqa
        ACCORDION_NAME = "Database"

        tree = ManageIQTree()

    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.settings.select_item('Configuration')
