from navmazing import NavigateToSibling
from widgetastic.widget import View

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ManageIQTree


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

    def step(self, *args, **kwargs):
        self.view.navigation.select("Optimize", "Bottlenecks")
