# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute
from widgetastic_manageiq import ParametrizedStatusBox

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils.appliance import Navigatable
from cfme.utils.wait import wait_for


class ContainersOverview(Navigatable):
    pass


class ContainersOverviewView(BaseLoggedInPage):
    status_cards = ParametrizedStatusBox()
    # TODO: Add widgets for utilization trends

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Containers', 'Overview']


@navigator.register(ContainersOverview, 'All')
class All(CFMENavigateStep):
    VIEW = ContainersOverviewView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Overview')

    def resetter(self):
        # We should wait ~2 seconds for the StatusBox population
        wait_for(lambda: self.view.status_cards('Providers').value,
                 num_sec=10, delay=1, silent_failure=True)
