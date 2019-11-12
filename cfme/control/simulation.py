from navmazing import NavigateToSibling
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Checkbox
from widgetastic.widget import Select
from widgetastic.widget import View
from widgetastic_patternfly import Button

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import SquashButton


class ControlSimulationView(BaseLoggedInPage):
    """Basic view for Control/Simulation tab."""
    fill_strategy = WaitFillViewStrategy()
    event_type = Select(id="event_typ")
    event_value = Select(id="event_value")
    filter_type = Select(id="filter_typ")
    filter_value = Select(id="filter_value")
    submit_button = Button("Submit")
    reset_button = Button("Reset")

    @View.nested
    class options(View):  # noqa
        out_of_scope = Checkbox(name="out_of_scope")
        show_successful = Checkbox(name="passed")
        show_failed = Checkbox(name="failed")

    @View.nested
    class simulation_results(View):  # noqa
        squash_button = SquashButton()
        tree = ManageIQTree("rsop_treebox")

    @property
    def is_displayed(self):
        return (
            self.event_type.is_displayed and
            self.filter_type.is_displayed and
            self.submit_button.is_displayed and
            self.reset_button.is_displayed
        )


@navigator.register(Server)
class ControlSimulation(CFMENavigateStep):
    VIEW = ControlSimulationView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self, *args, **kwargs):
        self.view.navigation.select("Control", "Simulation")
