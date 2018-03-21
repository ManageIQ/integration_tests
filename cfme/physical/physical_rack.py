# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalRack in CFME."""
import attr

from cached_property import cached_property
from navmazing import NavigateToAttribute

from cfme.common import Taggable
from cfme.common.physical_rack_views import (
    PhysicalRackDetailsView,
    PhysicalRacksView,
)
from cfme.exceptions import (
    ItemNotFound,
    StatsDoNotMatch,
    HostStatsNotContains,
    ProviderHasNoProperty
)
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


@attr.s
class PhysicalRack(BaseEntity, Updateable, Pretty, Taggable):
    """Model of an Physical Rack in cfme.

    Args:
        name: Name of the physical rack.
        custom_ident: The custom identifiter.
        provider: The physical provider.

    Usage:

        myrack = PhysicalRack()
        myrack.create()

    """
    pretty_attrs = ['name', 'custom_ident']

    name = attr.ib()
    provider = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    db_id = None

    INVENTORY_TO_MATCH = ['power_state']
    STATS_TO_MATCH = ['cores_capacity', 'memory_capacity']

    def load_details_page(self, refresh=False):
        """Load the PhysicalRack details page.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def refresh(self, cancel=False):
        """Perform 'Refresh Relationships and Power States' for the rack.

        Args:
            cancel (bool): Whether the action should be cancelled, default to False
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
            handle_alert=cancel)

    def wait_for_physical_rack_state_change(self, desired_state, timeout=300):
        """Wait for PhysicalRack to come to desired state. This function waits just the needed amount of
           time thanks to wait_for.

        Args:
            desired_state (str): 'on' or 'off'
            timeout (int): Specify amount of time (in seconds) to wait until TimedOutError is raised
        """
        view = navigate_to(self.parent, "All")

        def _looking_for_state_change():
            entity = view.entities.get_entity(name=self.name)
            return "currentstate-{}".format(desired_state) in entity.data['state']

        wait_for(_looking_for_state_change, fail_func=view.browser.refresh, num_sec=timeout)

    @property
    def exists(self):
        """Checks if the physical_rack exists in the UI.

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
            self.db_id = self.appliance.physical_rack_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def wait_to_appear(self):
        """Waits for the rack to appear in the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the rack to appear...")
        wait_for(
            lambda: self.exists,
            message="Wait for the rack to appear",
            num_sec=1000,
            fail_func=view.browser.refresh
        )

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the physical rack's information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. An exception will be raised
        if the stats retrieved from the UI do not match those retrieved from wrapanapi.
        """

        # Retrieve the client and the stats and inventory to match
        client = self.provider.mgmt
        stats_to_match = self.STATS_TO_MATCH
        inventory_to_match = self.INVENTORY_TO_MATCH

        # Retrieve the stats and inventory from wrapanapi
        rack_stats = client.stats(*stats_to_match, requester=self)
        rack_inventory = client.inventory(*inventory_to_match, requester=self)

        # Refresh the browser
        if ui:
            self.load_details(refresh=True)

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            try:
                cfme_stat = int(getattr(self, stat)(method='ui' if ui else None))
                rack_stat = int(rack_stats[stat])

                if rack_stat != cfme_stat:
                    msg = "The {} stat does not match. (rack: {}, rack stat: {}, cfme stat: {})"
                    raise StatsDoNotMatch(msg.format(stat, self.name, rack_stat, cfme_stat))
            except KeyError:
                raise HostStatsNotContains(
                    "Rack stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))

        # Verify that the inventory retrieved from wrapanapi match those retrieved
        # from the UI
        for inventory in inventory_to_match:
            try:
                cfme_inventory = getattr(self, inventory)(method='ui' if ui else None)
                rack_inventory = rack_inventory[inventory]

                if rack_inventory != cfme_inventory:
                    msg = "The {} inventory does not match. (rack: {}, rack inventory: {}, " \
                          "cfme inventory: {})"
                    raise StatsDoNotMatch(msg.format(inventory, self.name, rack_inventory,
                                                     cfme_inventory))
            except KeyError:
                raise HostStatsNotContains(
                    "Rack inventory information does not contain '{}'".format(inventory))
            except AttributeError:
                msg = "Provider does not know how to get '{}'"
                raise ProviderHasNoProperty(msg.format(inventory))


@attr.s
class PhysicalRackCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalRack`."""

    ENTITY = PhysicalRack

    def select_entity_rows(self, physical_racks):
        """ Select all physical rack objects """
        physical_racks = list(physical_racks)
        checked_physical_racks = list()
        view = navigate_to(self, 'All')

        for physical_rack in physical_racks:
            view.entities.get_entity(name=physical_rack.name, surf_pages=True).check()
            checked_physical_racks.append(physical_rack)
        return view

    def all(self):
        """returning all physical_racks objects"""
        physical_rack_table = self.appliance.db.client['physical_racks']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_rack_query = (
            self.appliance.db.client.session
                .query(physical_rack_table.name, ems_table.name)
                .join(ems_table, physical_rack_table.ems_id == ems_table.id))
        provider = None

        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            physical_rack_query = physical_rack_query.filter(ems_table.name == provider.name)
        physical_racks = []
        for name, ems_name in physical_rack_query.all():
            physical_racks.append(self.instantiate(name=name,
                                                   provider=provider or get_crud_by_name(ems_name)))
        return physical_racks


@navigator.register(PhysicalRackCollection)
class All(CFMENavigateStep):
    VIEW = PhysicalRacksView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Racks")


@navigator.register(PhysicalRack)
class Details(CFMENavigateStep):
    VIEW = PhysicalRackDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
