from cfme.utils.appliance import Navigatable
from navmazing import NavigateToAttribute
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class Utilization(Navigatable):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


@navigator.register(Utilization, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Optimize', 'Utilization')
