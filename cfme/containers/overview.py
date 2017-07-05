# -*- coding: utf-8 -*-
from __future__ import absolute_import
from functools import partial

from navmazing import NavigateToAttribute

from cfme.containers.provider import ContainersProvider
from cfme.web_ui import match_location, StatusBox
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from utils.appliance import Navigatable
from utils.wait import wait_for


match_page = partial(match_location, controller='container_dashboard', title='Container Dashboards')


class ContainersOverview(Navigatable):
    pass


@navigator.register(ContainersOverview, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page()

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Overview')

    def resetter(self):
        # We should wait ~2 seconds for the StatusBox population
        wait_for(lambda: StatusBox(ContainersProvider.PLURAL.split(' ')[-1]).value(),
                 num_sec=10, delay=1)
