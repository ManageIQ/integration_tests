from cfme.common import TopologyMixin
from navmazing import NavigateToAttribute
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import Navigatable


class NetworkTopology(TopologyMixin, Navigatable):
    ''' Class representing topology of networks in sdn '''

    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    @classmethod
    def load_topology_page(cls):
        navigate_to(NetworkTopology, 'All')


@navigator.register(NetworkTopology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Topology')
