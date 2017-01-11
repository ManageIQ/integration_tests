# -*- coding: utf-8 -*-
from functools import partial
from cfme.utils.appliance import Navigatable
from cfme.common import Taggable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from navmazing import NavigateToAttribute
from cfme.web_ui import match_location


match_page = partial(match_location, controller='container_dashboard', title='Container Dashboards')


class ContainersOverview(Taggable, Navigatable):
    pass


@navigator.register(ContainersOverview, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page()

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Containers', 'Overview')(None)

    def resetter(self):
        pass
