from cfme.common import TopologyMixin
from navmazing import NavigateToAttribute
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to


class MiddlewareTopology(TopologyMixin):

    @classmethod
    def load_topology_page(cls):
        navigate_to(MiddlewareTopology, 'All')


@navigator.register(MiddlewareTopology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Topology')
