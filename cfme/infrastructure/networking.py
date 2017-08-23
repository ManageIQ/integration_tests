from cfme.utils.appliance import Navigatable
from navmazing import NavigateToAttribute
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.web_ui import toolbar as tb


class InfraNetworking(Navigatable):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


@navigator.register(InfraNetworking, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Networking')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
