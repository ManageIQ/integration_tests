from widgetastic.utils import Fillable

from navmazing import NavigateToObject

from cfme.base.ui import BaseLoggedInPage
from cfme.utils.pretty import Pretty
from cfme.common.provider import BaseProvider
from cfme.utils.appliance import Navigatable
from cfme.utils.varmeth import variable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep

from cfme.base.ui import Server


class PhysicalProvider(Pretty, BaseProvider, Fillable):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.
    """
    provider_types = {}
    category = "physical"
    pretty_attrs = ['name']
    STATS_TO_MATCH = ['num_server']
    # string_name = "Physical Infrastructure"
    # page_name = "infrastructure"
    # db_types = ["InfraManager"]

    def __init__(
            self, appliance, name):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name

    @variable(alias='db')
    def num_server(self):
        pass

    @num_server.variant('ui')
    def num_server_ui(self):
        pass


@navigator.register(Server, 'PhysicalProviders')
@navigator.register(PhysicalProvider, 'All')
class All(CFMENavigateStep):
    # This view will need to be created
    VIEW = BaseLoggedInPage
    prerequisite = NavigateToObject(Server, 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Physical Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        pass
