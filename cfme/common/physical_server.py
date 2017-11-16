# -*- coding: utf-8 -*-
"""Module containing classes with common behaviour for both VMs and Instances of all types."""
from datetime import date
from functools import partial

from wrapanapi import exceptions

from cfme import js
from cfme.exceptions import (
    ItemNotFound, OptionNotAvailable, UnknownProviderType)
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    AngularCalendarInput, AngularSelect, Form, InfoBlock, Input, Select, fill, flash,
    form_buttons, toolbar, PagedTable, search, CheckboxTable,
    DriftGrid, BootstrapTreeview
)
import cfme.web_ui.toolbar as tb
from cfme.common import WidgetasticTaggable
from cfme.utils import version, ParamClassName
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for, TimedOutError

from . import PolicyProfileAssignable, SummaryMixin

access_btn = partial(toolbar.select, "Access")
cfg_btn = partial(toolbar.select, "Configuration")
lcl_btn = partial(toolbar.select, "Lifecycle")
mon_btn = partial(toolbar.select, 'Monitoring')
pol_btn = partial(toolbar.select, "Policy")
pwr_btn = partial(toolbar.select, "Power")


def base_types():
    from pkg_resources import iter_entry_points
    search = "physical_server"
    return {
        ep.name: ep.resolve() for ep in iter_entry_points('manageiq.{}_categories'.format(search))
    }


def instance_types(category):
    from pkg_resources import iter_entry_points
    search = "physical_server"
    return {
        ep.name: ep.resolve() for ep in iter_entry_points(
            'manageiq.{}_types.{}'.format(search, category))
    }


def all_types():
    all_types = base_types()
    for category in all_types.keys():
        all_types.update(instance_types(category))
    return all_types


class BasePhysicalServer(Pretty, Updateable, PolicyProfileAssignable, WidgetasticTaggable,
             SummaryMixin, Navigatable):
    """Base Physical Server class that holds the largest common functionality between physical ser
    instances, template

    In order to inherit these, you have to implement the ``on_details`` method.
    """
    pretty_attrs = ['name', 'provider']

    # Forms
    edit_form = Form(
        fields=[
            ('custom_ident', Input("custom_1")),
            ('description_tarea', "//textarea[@id='description']"),
            ('parent_sel', {
                version.LOWEST: Select("//select[@name='chosen_parent']"),
                "5.5": AngularSelect("chosen_parent")}),
            ('child_sel', Select("//select[@id='kids_chosen']", multi=True)),
            ('physical_server_sel', Select("//select[@id='choices_chosen']", multi=True))
        ])

    ###
    # Factory class methods
    #
    @classmethod
    def factory(cls, physical_server_name, provider):
        """Factory class method that determines the correct subclass for given provider.

        For reference how does that work, refer to the entrypoints in the setup.py

        Args:
            vm_name: Name of the VM/Instance as it appears in the UI
            provider: The provider object (not the string!)
            template_name: Source template name. Useful when the VM/Instance does not exist and you
                want to create it.
            template: Whether the generated object class should be VM/Instance or a template class.
        """
        try:
            return all_types(template)[provider.type](vm_name, provider, template_name)
        except KeyError:
            # Matching via provider type failed. Maybe we have some generic classes for infra/cloud?
            try:
                return all_types(template)[provider.category](vm_name, provider, template_name)
            except KeyError:
                raise UnknownProviderType(
                    'Unknown type of provider CRUD object: {}'
                    .format(provider.__class__.__name__))

    ###
    # To be set or implemented
    #
    ALL_LIST_LOCATION = None
    TO_OPEN_EDIT = None  # Name of the item in Configuration that puts you in the form
    QUADICON_TYPE = "physical_server"
    _param_name = ParamClassName('name')

    ###
    # Shared behaviour
    #
    def __init__(self, name, provider, appliance=None):
        super(BaseVM, self).__init__()
        Navigatable.__init__(self, appliance=appliance)
        if type(self) in {BaseVM, PhysicalServer }:
            raise NotImplementedError('This class cannot be instantiated.')
        self.name = name
        self.provider = provider

    ###
    # Properties
    #
    @property
    def is_physical_server(self):
        return not isinstance(self, _PhysicalServerMixin)

    @property
    def quadicon_type(self):
        return self.QUADICON_TYPE

    @property
    def paged_table(self):
        return PagedTable('//table')


    @property
    def exists(self):
        """Checks presence of the quadicon in the CFME."""
        try:
            self.find_quadicon()
            return True
        except VmOrInstanceNotFound:
            return False

    @property
    def ip_address(self):
        """Fetches IP Address of VM"""
        return self.provider.mgmt.get_ip_address(self.name)

    def find_quadicon(self, from_any_provider=False, use_search=True):
        """Find and return a quadicon belonging to a specific vm

        Args:
            from_any_provider: Whether to look for it anywhere (root of the tree). Useful when
                looking up archived or orphaned VMs

        Returns: entity of appropriate type
        Raises: VmOrInstanceNotFound
        """
        # todo :refactor this method replace it with vm methods like get_state
        if from_any_provider:
            view = navigate_to(self, 'All')
        else:
            view = navigate_to(self, 'AllForProvider', use_resetter=False)

        if 'Grid View' != view.toolbar.view_selector.selected:
            view.toolbar.view_selector.select('Grid View')

        if use_search:
            search.normal_search(self.name)

        try:
            return view.entities.get_entity(name=self.name, surf_pages=True)
        except ItemNotFound:
            raise VmOrInstanceNotFound("VM '{}' not found in UI!".format(self.name))

    def get_detail(self, properties=None, icon_href=False):
        """Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific PhysicalServer.

        Args:
            properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns:
            A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        if icon_href:
            return InfoBlock.icon_href(*properties)
        else:
            return InfoBlock.text(*properties)

    def open_details(self, properties=None):
        """Clicks on details infoblock"""
        self.load_details(refresh=True)
        sel.click(InfoBlock(*properties))

    @classmethod
    def get_first_physical_server(cls, provider):
        """Get first PhysicalServer."""
        # todo: move this to base provider ?
        view = navigate_to(cls, 'AllForProvider', provider=provider)
        return view.entities.get_first_entity()

    def load_details(self, refresh=False, from_any_provider=False):
        """Navigates to an PhysicalServer's details page.

        Args:
            refresh: Refreshes the PhysicalServer page if already there
            from_any_provider: 

        Raises:
            VmOrInstanceNotFound:
                When unable to find the VM passed
        """
        if from_any_provider:
            navigate_to(self, 'AnyProviderDetails', use_resetter=False)
        else:
            navigate_to(self, 'Details', use_resetter=False)
        if refresh:
            toolbar.refresh()
            self.browser.plugin.ensure_page_safe()

    def open_timelines(self):
        """Navigates to an VM's timeline page.

        Returns:
            :py:class:`TimelinesView` object
        """
        return navigate_to(self, 'Timelines')

    def refresh_relationships(self, from_details=False, cancel=False, from_any_provider=False):
        """Executes a refresh of relationships.

        Args:
            from_details: Whether or not to perform action from instance details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(from_any_provider=from_any_provider).check()
        cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
        sel.handle_alert(cancel=cancel)


    def wait_to_appear(self, timeout=600, load_details=True):
        """Wait for a PhysicalServer to appear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
            load_details: when found, should it load the vm details
        """
        def _refresh():
            self.provider.refresh_provider_relationships()
            self.appliance.browser.widgetastic.browser.refresh()  # strange because ViaUI

        wait_for(
            lambda: self.exists,
            num_sec=timeout, delay=5, fail_func=_refresh,
            message="wait for vm to appear")
        if load_details:
            self.load_details()

    def get_detail(self, properties=None, icon_href=False):
        """Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific VM/Instance.

        Args:
            properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns:
            A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        if icon_href:
            return InfoBlock.icon_href(*properties)
        else:
            return InfoBlock.text(*properties)


    def open_details(self, properties=None):
        """Clicks on details infoblock"""
        self.load_details(refresh=True)
        sel.click(InfoBlock(*properties))

    @classmethod
    def get_first_physical_server(cls, provider):
        """Get first VM/Instance."""
        # todo: move this to base provider ?
        view = navigate_to(cls, 'AllForProvider', provider=provider)
        return view.entities.get_first_entity()


    def load_details(self, refresh=False, from_any_provider=False):
        """Navigates to an PhysiclServer's details page.

        Args:
            refresh: Refreshes the PhysicalServer page if already there
            from_any_provider: 

        Raises:
            VmOrInstanceNotFound:
                When unable to find the VM passed
        """
        if from_any_provider:
            navigate_to(self, 'AnyProviderDetails', use_resetter=False)
        else:
            navigate_to(self, 'Details', use_resetter=False)
        if refresh:
            toolbar.refresh()
            self.browser.plugin.ensure_page_safe()

    def open_timelines(self):
        """Navigates to an VM's timeline page.

        Returns:
            :py:class:`TimelinesView` object
        """
        return navigate_to(self, 'Timelines')

    def refresh_relationships(self, from_details=False, cancel=False, from_any_provider=False):
        """Executes a refresh of relationships.

        Args:
            from_details: Whether or not to perform action from instance details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(from_any_provider=from_any_provider).check()
        cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

class PhysicalServer(BasePhysicalServer):

    def power_control_from_provider(self):
        raise NotImplementedError("You have to implement power_control_from_provider!")

    def power_control_from_cfme(self, option, cancel=True, from_details=False):
        """Power controls a VM from within CFME

        Args:
            option: corresponds to option values under the power button
            cancel: Whether or not to cancel the power operation on confirmation
