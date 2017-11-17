# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalServer in CFME."""
import attr

from cfme.common import PolicyProfileAssignable, WidgetasticTaggable

from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


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

    def get_power_state(self):
        return self.get_detail("Properties", "Power State")

    def refresh(self, cancel=False):
        """Perform 'Refresh Relationships and Power States' for the host.

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

        return wait_for(
            _looking_for_state_change,
            fail_func=view.browser.refresh,
            num_sec=timeout
        )

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

    def get_db_id(self):
        if self.db_id is None:
            self.db_id = self.appliance.physical_server_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def wait_to_appear(self):
        """Waits for the host to appear in the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the host to appear...")
        wait_for(
            lambda: self.exists,
            message="Wait for the server to appear",
            num_sec=1000,
            fail_func=view.browser.refresh
        )

    def wait_for_delete(self):
        """Waits for the host to remove from the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for a host to delete...")
        wait_for(
            lambda: not self.exists,
            message="Wait for the server to disappear",
            num_sec=500,
            fail_func=view.browser.refresh
        )


@attr.s
class PhysicalServerCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalServer`."""

    ENTITY = PhysicalServer

    def check_physical_servers(self, physical_servers):
        physical_servers = list(physical_servers)
        checked_physical_servers = list()
        view = navigate_to(self, 'All')

        for physical_server in physical_servers:
            try:
                view.entities.get_entity(name=physical_server.name, surf_pages=True).check()
                checked_physical_servers.append(physical_server)
            except ItemNotFound:
                raise (ItemNotFound(
                       'Could not find physical server {} in the UI'.format(physical_server.name)))
        return view

    def all(self, provider):
        """returning all physical_servers objects"""
        view = navigate_to(self, 'All')
        physical_servers = [self.instantiate(name=item, provider=provider)
                 for item in view.entities.entity_names]
        return physical_servers

    def power_on(self, *physical_servers):
        view = self.check_physical_servers(physical_servers)
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self, *physical_servers):
        view = self.check_physical_servers(physical_servers)
        view.toolbar.power.item_select("Power Off", handle_alert=True)
