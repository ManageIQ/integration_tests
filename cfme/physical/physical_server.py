"""A model of an Infrastructure PhysicalServer in CFME."""
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from wrapanapi.systems import LenovoSystem

from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.common.physical_server_views import PhysicalServerDetailsView
from cfme.common.physical_server_views import PhysicalServerEditTagsView
from cfme.common.physical_server_views import PhysicalServerManagePoliciesView
from cfme.common.physical_server_views import PhysicalServerNetworkDevicesView
from cfme.common.physical_server_views import PhysicalServerProvisionView
from cfme.common.physical_server_views import PhysicalServerStorageDevicesView
from cfme.common.physical_server_views import PhysicalServersView
from cfme.common.physical_server_views import PhysicalServerTimelinesView
from cfme.exceptions import HostStatsNotContains
from cfme.exceptions import ItemNotFound
from cfme.exceptions import ProviderHasNoProperty
from cfme.exceptions import StatsDoNotMatch
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for


@attr.s
class PhysicalServer(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, Taggable):
    """Model of an Physical Server in cfme.

    Args:
        name: Name of the physical server.
        hostname: hostname of the physical server.
        ip_address: The IP address as a string.
        custom_ident: The custom identifiter.

    Usage:

        myhost = PhysicalServer(name='vmware')
        myhost.create()

    """
    pretty_attrs = ['name', 'hostname', 'ip_address', 'custom_ident']

    name = attr.ib()
    ems_ref = attr.ib(default=None)
    provider = attr.ib(default=None)
    hostname = attr.ib(default=None)
    ip_address = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    db_id = None
    mgmt_class = LenovoSystem

    INVENTORY_TO_MATCH = ['power_state']
    STATS_TO_MATCH = ['cores_capacity', 'memory_capacity',
                      'num_network_devices', 'num_storage_devices']

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def _execute_button(self, button, option, handle_alert=False):
        view = navigate_to(self, "Details")
        view.toolbar.custom_button(button).item_select(option, handle_alert=handle_alert)
        return view

    def _execute_action_button(self, button, option, handle_alert=True, **kwargs):
        target = kwargs.get("target", None)
        provider = kwargs.get("provider", None)
        desired_state = kwargs.get("desired_state", None)

        view = self._execute_button(button, option, handle_alert=handle_alert)

        if desired_state:
            self._wait_for_state_change(desired_state, target, provider, view)
        elif handle_alert:
            wait_for(
                lambda: view.flash.is_displayed,
                message="Wait for the handle alert to appear...",
                num_sec=5,
                delay=2
            )

    def power_on(self, **kwargs):
        self._execute_action_button("Power", "Power On", **kwargs)

    def power_off(self, **kwargs):
        self._execute_action_button("Power", "Power Off", **kwargs)

    def power_off_immediately(self, **kwargs):
        self._execute_action_button("Power", "Power Off Immediately", **kwargs)

    def restart(self, **kwargs):
        self._execute_action_button("Power", "Restart", **kwargs)

    def restart_immediately(self, **kwargs):
        self._execute_action_button("Power", "Restart Immediately", **kwargs)

    def refresh(self, provider, handle_alert=False):
        last_refresh = provider.last_refresh_date()
        self._execute_button("Configuration", "Refresh Relationships and Power States",
                             handle_alert)
        wait_for(
            lambda: last_refresh != provider.last_refresh_date(),
            message="Wait for the server to be refreshed...",
            num_sec=300,
            delay=5
        )

    def turn_on_led(self, **kwargs):
        self._execute_action_button('Identify', 'Turn On LED', **kwargs)

    def turn_off_led(self, **kwargs):
        self._execute_action_button('Identify', 'Turn Off LED', **kwargs)

    def turn_blink_led(self, **kwargs):
        self._execute_action_button('Identify', 'Blink LED', **kwargs)

    @variable(alias='ui')
    def power_state(self):
        view = navigate_to(self, "Details")
        return view.entities.power_management.get_text_of("Power State")

    @variable(alias='ui')
    def cores_capacity(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("CPU total cores")

    @variable(alias='ui')
    def memory_capacity(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Total memory (mb)")

    @variable(alias='ui')
    def num_network_devices(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Network Devices")

    @variable(alias='ui')
    def num_storage_devices(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Storage Devices")

    def _wait_for_state_change(self, desired_state, target, provider, view, timeout=300, delay=10):
        """Wait for PhysicalServer to come to desired state. This function waits just the needed amount of
           time thanks to wait_for.

        Args:
            desired_state (str): 'on' or 'off'
            target (str): The name of the method that most be used to compare with the desired_state
            view (object): The view that most be refreshed to verify if the value was changed
            provider (object): 'LenovoProvider'
            timeout (int): Specify amount of time (in seconds) to wait until TimedOutError is raised
            delay (int): Specify amount of time (in seconds) to repeat each time.
        """

        def _is_state_changed():
            self.refresh(provider, handle_alert=True)
            return desired_state == getattr(self, target)()

        wait_for(_is_state_changed, fail_func=view.browser.refresh, num_sec=timeout, delay=delay)

    @property
    def exists(self):
        """Checks if the physical_server exists in the UI.

        Returns: :py:class:`bool`
        """
        view = navigate_to(self.parent, "All")
        try:
            view.entities.get_entity(name=self.name, surf_pages=True)
        except ItemNotFound:
            return False
        else:
            return True

    @cached_property
    def get_db_id(self):
        if self.db_id is None:
            self.db_id = self.appliance.physical_server_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def wait_to_appear(self):
        """Waits for the server to appear in the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the server to appear...")
        wait_for(
            lambda: self.exists,
            message="Wait for the server to appear",
            num_sec=1000,
            fail_func=view.browser.refresh
        )

    def wait_for_delete(self):
        """Waits for the server to remove from the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the server to delete...")
        wait_for(
            lambda: not self.exists,
            message="Wait for the server to disappear",
            num_sec=500,
            fail_func=view.browser.refresh
        )

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the physical server's information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. An exception will be raised
        if the stats retrieved from the UI do not match those retrieved from wrapanapi.
        """

        # Make sure we are on the physical server detail page
        if ui:
            self.load_details()

        # Retrieve the client and the stats and inventory to match
        client = self.provider.mgmt
        stats_to_match = self.STATS_TO_MATCH
        inventory_to_match = self.INVENTORY_TO_MATCH

        # Retrieve the stats and inventory from wrapanapi
        server_stats = client.server_stats(self, stats_to_match)
        server_inventory = client.server_inventory(self, inventory_to_match)

        # Refresh the browser
        if ui:
            self.browser.selenium.refresh()

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            try:
                cfme_stat = int(getattr(self, stat)(method='ui' if ui else None))
                server_stat = int(server_stats[stat])

                if server_stat != cfme_stat:
                    msg = "The {} stat does not match. (server: {}, server stat: {}, cfme stat: {})"
                    raise StatsDoNotMatch(msg.format(stat, self.name, server_stat, cfme_stat))
            except KeyError:
                raise HostStatsNotContains(
                    "Server stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))

        # Verify that the inventory retrieved from wrapanapi match those retrieved
        # from the UI
        for inventory in inventory_to_match:
            try:
                cfme_inventory = getattr(self, inventory)(method='ui' if ui else None)
                server_inventory = server_inventory[inventory]

                if server_inventory != cfme_inventory:
                    msg = "The {} inventory does not match. (server: {}, server inventory: {}, " \
                          "cfme inventory: {})"
                    raise StatsDoNotMatch(msg.format(inventory, self.name, server_inventory,
                                                     cfme_inventory))
            except KeyError:
                raise HostStatsNotContains(
                    "Server inventory information does not contain '{}'".format(inventory))
            except AttributeError:
                msg = "Provider does not know how to get '{}'"
                raise ProviderHasNoProperty(msg.format(inventory))


@attr.s
class PhysicalServerCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalServer`."""

    ENTITY = PhysicalServer

    def select_entity_rows(self, physical_servers):
        """ Select all physical server objects """
        physical_servers = list(physical_servers)
        checked_physical_servers = list()
        view = navigate_to(self, 'All')

        for physical_server in physical_servers:
            view.entities.get_entity(name=physical_server.name, surf_pages=True).ensure_checked()
            checked_physical_servers.append(physical_server)
        return view

    def all(self, provider):
        """returning all physical_servers objects"""
        physical_server_table = self.appliance.db.client['physical_servers']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_server_query = (
            self.appliance.db.client.session
                .query(physical_server_table.name, physical_server_table.ems_ref, ems_table.name)
                .join(ems_table, physical_server_table.ems_id == ems_table.id))
        provider = None

        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            physical_server_query = physical_server_query.filter(ems_table.name == provider.name)
        physical_servers = []
        for name, ems_ref, ems_name in physical_server_query.all():
            physical_servers.append(self.instantiate(name=name, ems_ref=ems_ref,
                                    provider=provider or get_crud_by_name(ems_name)))
        return physical_servers

    def find_by(self, provider, ph_name):
        """returning all physical_servers objects"""
        physical_server_table = self.appliance.db.client['physical_servers']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_server_query = (
            self.appliance.db.client.session
                .query(physical_server_table.name, ems_table.name)
                .join(ems_table, physical_server_table.ems_id == ems_table.id))
        provider = None

        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            physical_server_query = physical_server_query.filter(ems_table.name == provider.name)

        for name, ems_name in physical_server_query.all():
            if ph_name == name:
                return self.instantiate(name=name, provider=provider or get_crud_by_name(ems_name))

    def power_on(self, *physical_servers):
        view = self.select_entity_rows(physical_servers)
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self, *physical_servers):
        view = self.select_entity_rows(physical_servers)
        view.toolbar.power.item_select("Power Off", handle_alert=True)

    def custom_button_action(self, button, option, physical_servers, handle_alert=True):
        view = self.select_entity_rows(physical_servers)
        view.toolbar.custom_button(button).item_select(option, handle_alert=handle_alert)


@navigator.register(PhysicalServerCollection)
class All(CFMENavigateStep):
    VIEW = PhysicalServersView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Servers")


@navigator.register(PhysicalServerCollection)
class ManagePoliciesCollection(CFMENavigateStep):
    VIEW = PhysicalServerManagePoliciesView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select("Manage Policies")


@navigator.register(PhysicalServerCollection)
class EditTagsCollection(CFMENavigateStep):
    VIEW = PhysicalServerEditTagsView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select("Edit Tags")


@navigator.register(PhysicalServerCollection)
class ProvisionCollection(CFMENavigateStep):
    VIEW = PhysicalServerProvisionView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Provision Physical Server")


@navigator.register(PhysicalServer)
class Details(CFMENavigateStep):
    VIEW = PhysicalServerDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(PhysicalServer)
class ManagePolicies(CFMENavigateStep):
    VIEW = PhysicalServerManagePoliciesView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select("Manage Policies")


@navigator.register(PhysicalServer)
class Provision(CFMENavigateStep):
    VIEW = PhysicalServerProvisionView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Provision Physical Server")


@navigator.register(PhysicalServer)
class Timelines(CFMENavigateStep):
    VIEW = PhysicalServerTimelinesView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select("Timelines")


@navigator.register(PhysicalServer)
class NetworkDevices(CFMENavigateStep):
    VIEW = PhysicalServerNetworkDevicesView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.properties.click_at("Network Devices")


@navigator.register(PhysicalServer)
class StorageDevices(CFMENavigateStep):
    VIEW = PhysicalServerStorageDevicesView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.properties.click_at("Storage Devices")
