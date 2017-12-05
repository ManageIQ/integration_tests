from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import Fillable

from cfme.base.ui import Server
from cfme.common.provider import BaseProvider
from cfme.common.provider_views import PhysicalProviderAddView, PhysicalProvidersView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.varmeth import variable


class PhysicalProvider(Pretty, BaseProvider, Fillable):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.
    """
    provider_types = {}
    category = "physical"
    pretty_attrs = ['name']
    STATS_TO_MATCH = ['num_server']
    # string_name = "Physical Infrastructure"
    # db_types = ["InfraManager"]

    def __init__(
            self, appliance=None, name=None, key=None, endpoints=None):
        Navigatable.__init__(self, appliance=appliance)
        self.endpoints = self._prepare_endpoints(endpoints)
        self.name = name
        self.key = key

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
    VIEW = PhysicalProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Physical Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        pass


@navigator.register(PhysicalProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = PhysicalProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Add a New Infrastructure Provider'
        )
