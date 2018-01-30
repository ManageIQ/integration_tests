# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalServer in CFME."""
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from cached_property import cached_property
from cfme.utils import conf
from cfme.common import PolicyProfileAssignable, WidgetasticTaggable
from cfme.common.physical_server_views import (
    PhysicalServerDetailsView,
    PhysicalServerManagePoliciesView,
    PhysicalServersView,
    PhysicalServerTimelinesView
)
from cfme.exceptions import ItemNotFound, StatsDoNotMatch, HostStatsNotContains
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from cfme.utils.providers import get_crud_by_name
from cfme.exceptions import ProviderHasNoProperty
from wrapanapi.lenovo import LenovoSystem
from cfme.utils.varmeth import variable

@attr.s
class PhysicalServer(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, WidgetasticTaggable):
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
    provider = attr.ib(default=None)
    hostname = attr.ib(default=None)
    ip_address = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    db_id = None
    mgmt_class = LenovoSystem

    STATS_TO_MATCH = ['power_state']

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def execute_button(self, button_group, button, handle_alert=False):
        view = navigate_to(self, "Details")
        view.toolbar.custom_button(button_group).item_select(button, handle_alert=handle_alert)

    def power_on(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power Off", handle_alert=True)

    @variable(alias='ui')
    def power_state(self):
        return self.get_detail("Power Management", "Power State")

    def refresh(self, cancel=False):
        """Perform 'Refresh Relationships and Power States' for the server.

        Args:
            cancel (bool): Whether the action should be cancelled, default to False
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
            handle_alert=cancel)

    def wait_for_physical_server_state_change(self, desired_state, timeout=300):
        """Wait for PhysicalServer to come to desired state. This function waits just the needed amount of
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

    def get_detail(self, title, field):
        """Gets details from the details summary tables.

        Args:
            title (str): Summary Table title
            field (str): Summary table field name

        Returns: A string representing the entities of the SummaryTable's value.
        """
        view = navigate_to(self, "Details")
        return getattr(view.entities, title.lower().replace(" ", "_")).get_text_of(field)

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

        # Retrieve the data from the provider
        providers_data = conf.cfme_data.get("management_systems", {})
        providers = providers_data

        # Gather the data necessary to instantiate an instance of the management class
        # defined in wrapanapi.
        provider_data = providers['lenovo']
        credentials = provider_data['credentials']
        credentials = conf.credentials[credentials]
        provider_kwargs = provider_data.copy()
        provider_kwargs.update(credentials)
        provider_kwargs['logger'] = logger

        # Create an instance of the management class
        mgmt = self.mgmt_class(**provider_kwargs)

        # Check that the stats match
        self._check_for_matching_stats(mgmt, self.STATS_TO_MATCH, ui=ui)

    def _check_for_matching_stats(self, client, stats_to_match=None, ui=False):
        """ A function that checks that the stats from CFME and wrapanapi match.

            If the stats do not match, an exception is raised.
        """
        # Retrieve the stats from wrapanapi
        host_stats = client.stats(*stats_to_match, requester=self)

        # Refresh the browser
        if ui:
            self.browser.selenium.refresh()

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            try:
                cfme_stat = getattr(self, stat)(method='ui' if ui else None)

                if host_stats[stat] != cfme_stat:
                    msg = "The {} stat does not match. (server: {}, host stat: {}, cfme stat: {})"
                    raise StatsDoNotMatch(msg.format(stat, self.name, host_stats[stat], cfme_stat))
            except KeyError:
                raise HostStatsNotContains(
                    "Host stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))


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
            view.entities.get_entity(name=physical_server.name, surf_pages=True).check()
            checked_physical_servers.append(physical_server)
        return view

    def all(self, provider):
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
        physical_servers = []
        for name, ems_name in physical_server_query.all():
            physical_servers.append(self.instantiate(name=name,
                                    provider=provider or get_crud_by_name(ems_name)))
        return physical_servers

    def power_on(self, *physical_servers):
        view = self.select_entity_rows(physical_servers)
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self, *physical_servers):
        view = self.select_entity_rows(physical_servers)
        view.toolbar.power.item_select("Power Off", handle_alert=True)


@navigator.register(PhysicalServerCollection)
class All(CFMENavigateStep):
    VIEW = PhysicalServersView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Servers")


@navigator.register(PhysicalServer)
class Details(CFMENavigateStep):
    VIEW = PhysicalServerDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(PhysicalServer)
class ManagePolicies(CFMENavigateStep):
    VIEW = PhysicalServerManagePoliciesView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select("Manage Policies")


@navigator.register(PhysicalServer)
class Timelines(CFMENavigateStep):
    VIEW = PhysicalServerTimelinesView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select("Timelines")
