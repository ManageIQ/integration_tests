# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute

from cfme.common import TopologyMixin
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import Navigatable


class Topology(TopologyMixin, Navigatable):

    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    @classmethod
    def load_topology_page(cls):
        navigate_to(cls, 'All')


@navigator.register(Topology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Containers', 'Topology')(None)
