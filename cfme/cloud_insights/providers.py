""" A model of an Infrastructure Provider in CFME
"""
import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from widgetastic_patternfly import SelectorDropdown

from cfme.base.login import BaseLoggedInPage
from cfme.infrastructure.host import HostsCollection
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Table
# from cfme.exceptions import displayed_not_implemented


class CloudInsightsProvidersView(BaseLoggedInPage):
    """Basic view for Red Hat Cloud/Services page."""

    global_sync_title = Text(locator='.//h1[normalize-space(.)="Global Synchronization"]')
    global_sync_subtext = Text(locator='.//p[@id="red_hat_cloud_providers_global_info"')
    sync_platform_button = Button("Synchronize this Platform to Cloud")
    provider_sync_title = Text(locator='.//h1[normalize-space(.)="Provider Synchronization"]')
    provider_sync_subtext = Text('.//p[@id="red_hat_cloud_services_table_info"')
    filter_dropdown = SelectorDropdown("id", "filter_input")
    filter_input_field = Input(id='filter_input')
    sync_table_button = Button(id="Synchronize")
    provider_sync_table = Table(
        './/table[@id="red_hat_cloud_providers_table")]',
        column_widgets={
            0: Checkbox(locator=".//input[@type='checkbox']"),
            "Action": Button(location='.//td/button[normalize-space(text())="Synchronize"]'),
        },
    )

    @property
    def is_displayed(self):
        return (self.global_sync_title.text == "Global Synchronization"
                and self.sync_platform_button.is_displayed
                and self.provider_sync_title == "Provider Synchronization"
                and self.provider_sync_table.is_displayed)


@attr.s
class CloudInsightsProviders(BaseEntity):

    provider = attr.ib(default=None)

    _collections = {'hosts': HostsCollection}


@attr.s
class CloudInsightsProvidersCollection(BaseCollection):

    ENTITY = CloudInsightsProviders

    def all(self):
        view = navigate_to(self, "All")
        providers = [self.collections.instantiate(name=row.name.text) for row in
                     view.provider_sync_table.rows()]
        return providers


# Red Hat Cloud - Insights
@navigator.register(CloudInsightsProvidersCollection, "All")
class CloudInsightsServices(CFMENavigateStep):
    VIEW = CloudInsightsProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.view.navigation.select("Red Hat Cloud", "Providers")
