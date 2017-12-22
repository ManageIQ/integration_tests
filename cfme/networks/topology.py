from navmazing import NavigateToAttribute

from cfme.common.topology import BaseTopologyElementsCollection, BaseTopologyView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator


class NetworkTopologyView(BaseTopologyView):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Networks", "Topology"]
        )


class NetworkTopologyElementsCollection(BaseTopologyElementsCollection):
    pass


@navigator.register(NetworkTopologyElementsCollection)
class All(CFMENavigateStep):
    VIEW = NetworkTopologyView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        self.view.navigation.select("Networks", "Topology")
