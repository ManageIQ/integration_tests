from cfme.common import TopologyMixin
from cfme.fixtures import pytest_selenium as sel
from navmazing import NavigateToAttribute
from utils.appliance.implementations.ui import CFMENavigateStep, navigator


class MiddlewareTopology(TopologyMixin):

    @classmethod
    def load_topology_page(cls):
        sel.force_navigate('middleware_topology')


@navigator.register(MiddlewareTopology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Middleware', 'Topology')(None)
