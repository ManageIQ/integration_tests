from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import Accordion, ManageIQTree

from cfme.base.login import BaseLoggedInPage
from cfme.base import Server
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class BottlenecksView(BaseLoggedInPage):
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Optimize', 'Bottlenecks'])

    @View.nested
    class bottlenecks(Accordion):  # noqa
        ACCORDION_NAME = "Bottlenecks"

        tree = ManageIQTree()


@navigator.register(Server)
class Bottlenecks(CFMENavigateStep):
    VIEW = BottlenecksView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Optimize", "Bottlenecks")
