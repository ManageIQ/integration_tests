# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import Select
from widgetastic_patternfly import Button

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ControlSimulationView(BaseLoggedInPage):
    """Basic view for Control/Simulation tab."""
    event_selection = Select(id="event_typ")
    vm_selection = Select(id="filter_typ")
    submit_button = Button("Submit")
    reset_button = Button("Reset")
    # TODO Add simulation results tree. That tree can
    # be shown only after filling aforedefined widgets.

    @property
    def is_displayed(self):
        return (
            self.event_selection.is_displayed and
            self.vm_selection.is_displayed and
            self.submit_button.is_displayed and
            self.reset_button.is_displayed
        )


@navigator.register(Server)
class ControlSimulation(CFMENavigateStep):
    VIEW = ControlSimulationView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Control", "Simulation")
