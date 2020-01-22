"""A model of an Infrastructure PhysicalSwitch in CFME."""
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute

from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.common.physical_switch_views import PhysicalSwitchDetailsView
from cfme.common.physical_switch_views import PhysicalSwitchesView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


@attr.s
class PhysicalSwitch(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, Taggable):
    """Model of an Physical Switch in cfme.

    Args:
        name: Name of the physical Switch.

    Usage:

        myswitch = PhysicalSwitch(name='sample_switch')
        myswitch.create()

    """
    pretty_attrs = ['name']

    name = attr.ib()
    provider = attr.ib(default=None)

    INVENTORY_TO_MATCH = ['power_state', 'part_number', 'serial_number', 'description',
                          'manufacturer']

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

    def power_state(self):
        view = navigate_to(self, "Details")
        return view.entities.power_management.get_text_of("Power State")

    def part_number(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Part Number")

    def serial_number(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Serial Number")

    def description(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Description")

    def manufacturer(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Manufacturer")

    def _wait_for_state_change(self, desired_state, target, provider, view, timeout=300, delay=10):
        """Wait for the Physical Switch to reach the desired state. This function waits an amount
           of time due to wait_for.

        Args:
            desired_state (str): 'on' or 'off'
            target (str): The name of the method that most be used to compare with the desired_state
            provider (object): 'LenovoProvider'
            view (object): The view that most be refreshed to verify if the value was changed
            timeout (int): Specify amount of time (in seconds) to wait until TimedOutError is raised
            delay (int): Specify amount of time (in seconds) to repeat each time.
        """

        def _is_state_changed():
            self.refresh(provider, handle_alert=True)
            return desired_state == getattr(self, target)()

        wait_for(_is_state_changed, fail_func=view.browser.refresh, num_sec=timeout, delay=delay)

    @property
    def exists(self):
        """Checks if the physical_switch exists in the UI.

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
    def db_id(self):
        return self.appliance.physical_switch_id(self.name)

    def wait_to_appear(self):
        """Waits for the Switch to appear in the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the Switch to appear...")
        wait_for(
            lambda: self.exists,
            message="Wait for the Switch to appear",
            num_sec=1000,
            fail_func=view.browser.refresh
        )

    def wait_for_delete(self):
        """Waits for the Switch to remove from the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the Switch to delete...")
        wait_for(
            lambda: not self.exists,
            message="Wait for the Switch to disappear",
            num_sec=500,
            fail_func=view.browser.refresh
        )


@attr.s
class PhysicalSwitchCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalSwitch`."""

    ENTITY = PhysicalSwitch

    def select_entity_rows(self, *physical_switches):
        """ Select all physical Switch objects """
        physical_switches = list(physical_switches)
        checked_physical_switches = list()
        view = navigate_to(self, 'All')

        for physical_switch in physical_switches:
            view.entities.get_entity(name=physical_switch.name, surf_pages=True).ensure_checked()
            checked_physical_switches.append(physical_switch)
        return view

    def all(self):
        """returning all physical_switches objects"""
        physical_switch_table = self.appliance.db.client['switches']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_switch_query = (
            self.appliance.db.client.session
                .query(physical_switch_table.name, ems_table.name)
                .join(ems_table, physical_switch_table.ems_id == ems_table.id))

        provider = self.filters.get('provider')
        if provider:
            physical_switch_query = physical_switch_query.filter(ems_table.name == provider.name)
        physical_switches = []
        for name, ems_name in physical_switch_query.all():
            physical_switches.append(self.instantiate(name=name,
                                    provider=provider or get_crud_by_name(ems_name)))
        return physical_switches

    def find_by(self, ph_name, provider=None):
        """returning all physical_switches objects"""
        physical_switch_table = self.appliance.db.client['switches']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_switch_query = (
            self.appliance.db.client.session
                .query(physical_switch_table.name, ems_table.name)
                .join(ems_table, physical_switch_table.ems_id == ems_table.id))

        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            physical_switch_query = physical_switch_query.filter(ems_table.name == provider.name)

        for name, ems_name in physical_switch_query.all():
            if ph_name == name:
                return self.instantiate(name=name, provider=provider or get_crud_by_name(ems_name))


@navigator.register(PhysicalSwitchCollection)
class All(CFMENavigateStep):
    VIEW = PhysicalSwitchesView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Switches")


@navigator.register(PhysicalSwitch)
class Details(CFMENavigateStep):
    VIEW = PhysicalSwitchDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
