# -*- coding: utf-8 -*-
"""Module containing classes with common behaviour for both VMs and Instances of all types."""
from datetime import datetime, date, timedelta
from functools import partial

from wrapanapi import exceptions
from widgetastic.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable
from cfme.common.vm_console import VMConsole
from cfme.common.vm_views import DriftAnalysis, DriftHistory, VMPropertyDetailView
from cfme.exceptions import (
    VmOrInstanceNotFound, ItemNotFound, OptionNotAvailable, UnknownProviderType)
from cfme.utils import ParamClassName
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for
from widgetastic_manageiq import VersionPick

from . import PolicyProfileAssignable, SummaryMixin


def base_types(template=False):
    from pkg_resources import iter_entry_points
    search = "template" if template else "vm"
    return {
        ep.name: ep.resolve() for ep in iter_entry_points('manageiq.{}_categories'.format(search))
    }


def instance_types(category, template=False):
    from pkg_resources import iter_entry_points
    search = "template" if template else "vm"
    return {
        ep.name: ep.resolve() for ep in iter_entry_points(
            'manageiq.{}_types.{}'.format(search, category))
    }


def all_types(template=False):
    all_types = base_types(template)
    for category in all_types.keys():
        all_types.update(instance_types(category, template))
    return all_types


class _TemplateMixin(object):
    pass


class BaseVM(Pretty, Updateable, PolicyProfileAssignable, WidgetasticTaggable,
             SummaryMixin, Navigatable):
    """Base VM and Template class that holds the largest common functionality between VMs,
    instances, templates and images.

    In order to inherit these, you have to implement the ``on_details`` method.
    """
    pretty_attrs = ['name', 'provider', 'template_name']

    ###
    # Factory class methods
    #
    @classmethod
    def factory(cls, vm_name, provider, template_name=None, template=False):
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
    QUADICON_TYPE = "vm"
    # Titles of the delete buttons in configuration
    REMOVE_SELECTED = 'Remove selected items'
    REMOVE_SINGLE = VersionPick({'5.8': 'Remove Virtual Machine',
                                 '5.9': 'Remove Virtual Machine from Inventory'})
    RETIRE_DATE_FMT = VersionPick({'5.8': parsetime.american_minutes_with_utc,
                                   '5.9': parsetime.saved_report_title_format})
    _param_name = ParamClassName('name')
    DETAILS_VIEW_CLASS = None

    ###
    # Shared behaviour
    #
    def __init__(self, name, provider, template_name=None, appliance=None):
        super(BaseVM, self).__init__()
        Navigatable.__init__(self, appliance=appliance)
        if type(self) in {BaseVM, VM, Template}:
            raise NotImplementedError('This class cannot be instantiated.')
        self.name = name
        self.provider = provider
        self.template_name = template_name

    ###
    # Properties
    #
    @property
    def is_vm(self):
        return not isinstance(self, _TemplateMixin)

    @property
    def quadicon_type(self):
        return self.QUADICON_TYPE

    ###
    # Methods
    #
    def check_compliance(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        view = navigate_to(self, "Details")
        original_state = self.compliance_status
        view.toolbar.policy.item_select("Check Compliance of Last Known Configuration",
            handle_alert=True)
        view.flash.assert_no_error()
        wait_for(
            lambda: self.compliance_status != original_state,
            num_sec=timeout, delay=5, message="compliance of {} checked".format(self.name)
        )

    @property
    def compliance_status(self):
        """Returns the title of the compliance SummaryTable. The title contains datetime so it can
        be compared.

        Returns:
            :py:class:`NoneType` if no title is present (no compliance checks before), otherwise str
        """
        view = navigate_to(self, "Details")
        view.browser.refresh()
        return self.get_detail("Compliance", "Status")

    @property
    def compliant(self):
        """Check if the VM is compliant.

        Returns:
            :py:class:`bool`
        """
        text = self.compliance_status.strip().lower()
        if text.startswith("non-compliant"):
            return False
        elif text.startswith("compliant"):
            return True
        else:
            raise ValueError("{} is not a known state for compliance".format(text))

    @property
    def console_handle(self):
        '''
        The basic algorithm for getting the consoles window handle is to get the
        appliances window handle and then iterate through the window_handles till we find
        one that is not the appliances window handle.   Once we find this check that it has
        a canvas widget with a specific ID
        '''
        browser = self.appliance.browser.widgetastic
        appliance_handle = browser.window_handle
        cur_handles = browser.selenium.window_handles
        logger.info("Current Window Handles:  {}".format(cur_handles))

        for handle in cur_handles:
            if handle != appliance_handle:
                # FIXME: Add code to verify the tab has the correct widget
                #      for a console tab.
                return handle

    @property
    def vm_console(self):
        """Get the consoles window handle, and then create a VMConsole object, and store
        the VMConsole object aside.
        """
        console_handle = self.console_handle

        if console_handle is None:
            raise TypeError("Console handle should not be None")

        appliance_handle = self.appliance.browser.widgetastic.window_handle
        logger.info("Creating VMConsole:")
        logger.info("   appliance_handle: {}".format(appliance_handle))
        logger.info("     console_handle: {}".format(console_handle))
        logger.info("               name: {}".format(self.name))

        return VMConsole(appliance_handle=appliance_handle,
                console_handle=console_handle,
                vm=self)

    def delete(self, cancel=False, from_details=False):
        """Deletes the VM/Instance from the VMDB.

        Args:
            cancel: Whether to cancel the action in the alert.
            from_details: Whether to use the details view or list view.
        """

        if from_details:
            view = navigate_to(self, 'Details')
            view.toolbar.configuration.item_select(self.REMOVE_SINGLE.pick(self.appliance.version),
                                                   handle_alert=not cancel)
        else:
            view = navigate_to(self, 'All')
            self.find_quadicon().check()
            view.toolbar.configuration.item_select(self.REMOVE_SELECTED, handle_alert=not cancel)

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

    @property
    def is_retired(self):
        """"Check retirement status of vm"""
        self.summary.reload()
        if self.summary.lifecycle.retirement_date.text_value.lower() != 'never':
            try:
                return self.summary.lifecycle.retirement_state.text_value.lower() == 'retired'
            except AttributeError:
                return False
        else:
            return False

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
        try:
            return view.entities.get_entity(name=self.name, surf_pages=True, use_search=use_search)
        except ItemNotFound:
            raise VmOrInstanceNotFound("VM '{}' not found in UI!".format(self.name))

    def get_detail(self, properties=None):
        """Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific VM/Instance.

        Args:
            properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns:
            A string representing the contents of the InfoBlock's value.
        """
        view = navigate_to(self, 'Details')
        return getattr(view.entities, properties[0].lower().replace(' ', '_')).get_text_of(
            properties[1])

    def open_console(self, console='VM Console', invokes_alert=False, cancel=False):
        """
        Initiates the opening of one of the console types supported by the Access
        button.   Presently we only support VM Console, which is the HTML5 Console.
        In case of VMware provider it could be VMRC, VNC/HTML5, WebMKS, but we only
        support VNC/HTML5.
        Possible values for 'console' could be 'VM Console' and 'Web Console', but Web
        Console is not supported as well.

        Args:
            console: one of the supported console types given by the Access button.
            invokes_alert: If the particular console will invoke a CFME popup/alert
                           setting this to true will handle this.
            cancel: Allows one to cancel the operation if the popup/alert occurs.
        """
        # TODO: implement vmrc vm console
        if console not in ['VM Console']:
            raise NotImplementedError('Not supported console type: {}'.format(console))

        view = navigate_to(self, 'Details')

        # Click console button given by type
        view.toolbar.access.item_select(console, handle_alert=not invokes_alert)
        self.vm_console

    def open_details(self, properties=None):
        """Clicks on details infoblock"""
        view = navigate_to(self, 'Details')
        getattr(view.entities, properties[0].lower().replace(' ', '_')).click_at(
            properties[1])
        return self.create_view(VMPropertyDetailView)

    @classmethod
    def get_first_vm(cls, provider):
        """Get first VM/Instance."""
        # todo: move this to base provider ?
        view = navigate_to(cls, 'AllForProvider', provider=provider)
        return view.entities.get_first_entity()

    @property
    def last_analysed(self):
        """Returns the contents of the ``Last Analysed`` field in summary"""
        return self.get_detail(properties=('Lifecycle', 'Last Analyzed')).strip()

    def load_details(self, refresh=False, from_any_provider=False):
        """Navigates to an VM's details page.

        Args:
            refresh: Refreshes the VM page if already there
            from_any_provider: Archived/Orphaned VMs need this
        """
        if from_any_provider:
            view = navigate_to(self, 'AnyProviderDetails', use_resetter=False)
        else:
            view = navigate_to(self, 'Details', use_resetter=False)
        if refresh:
            view.toolbar.reload.click()
        return view

    def open_edit(self):
        """Loads up the edit page of the object."""
        return navigate_to(self, 'Edit')

    def open_timelines(self):
        """Navigates to an VM's timeline page.

        Returns:
            :py:class:`TimelinesView` object
        """
        return navigate_to(self, 'Timelines')

    def rediscover(self):
        """Deletes the VM from the provider and lets it discover again"""
        self.delete(from_details=True)
        self.wait_for_delete()
        self.provider.refresh_provider_relationships()
        self.wait_to_appear()

    def rediscover_if_analysis_data_present(self):
        """Rediscovers the object if it has some analysis data present.

        Returns:
            Boolean if the rediscovery happened.
        """
        if self.last_analysed.lower() != 'never':
            self.rediscover()
            return True
        return False

    def refresh_relationships(self, from_details=False, cancel=False, from_any_provider=False):
        """Executes a refresh of relationships.

        Args:
            from_details: Whether or not to perform action from instance details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            view = self.load_details()
        else:
            view = navigate_to(self, 'All')
            self.find_quadicon(from_any_provider=from_any_provider).check()
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
                                               handle_alert=not cancel)

    @property
    def retirement_date(self):
        """Returns the retirement date of the selected machine, or 'Never'

        Returns:
            :py:class:`str` object
        """
        return self.get_detail(properties=("Lifecycle", "Retirement Date")).strip()

    def smartstate_scan(self, cancel=False, from_details=False):
        """Initiates fleecing from the UI.

        Args:
            cancel: Whether or not to cancel the refresh relationships action
            from_details: Whether or not to perform action from instance details page
        """
        if from_details:
            view = self.load_details()
        else:
            view = navigate_to(self, 'All')
            self.find_quadicon().check()
        view.toolbar.configuration.item_select('Perform SmartState Analysis',
                                               handle_alert=not cancel)

    def wait_to_disappear(self, timeout=600):
        """Wait for a VM to disappear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
        """
        wait_for(
            lambda: self.exists,
            num_sec=timeout, delay=30, fail_func=self.browser.refresh, fail_condition=True,
            message="wait for vm to not exist")

    wait_for_delete = wait_to_disappear  # An alias for more fitting verbosity

    def wait_to_appear(self, timeout=600, load_details=True):
        """Wait for a VM to appear within CFME

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

    def set_ownership(self, user=None, group=None, click_cancel=False, click_reset=False):
        """Set ownership of the VM/Instance or Template/Image"""
        view = navigate_to(self, "SetOwnership")
        view.form.fill({'user_name': user, 'group_name': group})
        if click_reset:
            view.form.reset_button.click()
        elif click_cancel:
            view.form.cancel_button.click()
        else:
            view.form.save_button.click()
        view.flash.assert_no_error()

    def unset_ownership(self):
        """Unset ownership of the VM/Instance or Template/Image"""
        # choose the vm code comes here
        view = navigate_to(self, "SetOwnership")
        view.form.fill({'user_name': '<No Owner>', 'group_name': 'EvmGroup-administrator'})
        view.form.save_button.click()
        view.flash.assert_no_error()


class VM(BaseVM):
    TO_RETIRE = None

    def retire(self):
        view = self.load_details(refresh=True)
        view.toolbar.configuration.item_select(self.TO_RETIRE,
                                               handle_alert=True)
        view.flash.assert_no_error()

    def power_control_from_provider(self):
        raise NotImplementedError("You have to implement power_control_from_provider!")

    def power_control_from_cfme(self, option, cancel=True, from_details=False):
        """Power controls a VM from within CFME

        Args:
            option: corresponds to option values under the power button
            cancel: Whether or not to cancel the power operation on confirmation
            from_details: Whether or not to perform action from instance details page

        Raises:
            OptionNotAvailable: option param is not visible or enabled
        """
        if from_details:
            view = self.load_details()
        else:
            view = navigate_to(self, 'All')

        if self.is_pwr_option_available_in_cfme(option=option, from_details=from_details):

                view.toolbar.power.item_select(option, handle_alert=not cancel)
                logger.info(
                    "Power control action of VM/instance %s, option %s, cancel %s executed",
                    self.name, option, str(cancel))
        else:
            raise OptionNotAvailable(option + " is not visible or enabled")

    def wait_candu_data_available(self, timeout=600):
        """Waits until C&U data are available for this VM/Instance

        Args:
            timeout: Timeout passed to :py:func:`utils.wait.wait_for`
        """
        view = self.load_details(refresh=True)
        wait_for(
            lambda: not view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=lambda: view.toolbar.reload.click)

    def wait_for_vm_state_change(self, desired_state=None, timeout=300, from_details=False,
                                 with_relationship_refresh=True, from_any_provider=False):
        """Wait for VM to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: on, off, suspended... for available states, see
                           :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
            timeout: Specify amount of time (in seconds) to wait
            from_any_provider: Archived/Orphaned vms need this
        Raises:
            TimedOutError:
                When instance does not come up to desired state in specified period of time.
            InstanceNotFound:
                When unable to find the instance passed
        """
        detail_t = ("Power Management", "Power State")

        def _looking_for_state_change():
            if from_details:
                self.load_details(refresh=True)
                return self.get_detail(properties=detail_t) == desired_state
            else:
                return 'currentstate-' + desired_state in self.find_quadicon(
                    from_any_provider=from_any_provider).data['state']

        return wait_for(
            _looking_for_state_change,
            num_sec=timeout,
            delay=30,
            fail_func=lambda: self.refresh_relationships(from_details=from_details,
                                                         from_any_provider=from_any_provider) if
            with_relationship_refresh else None)

    def is_pwr_option_available_in_cfme(self, option, from_details=False):
        """Checks to see if a power option is available on the VM

        Args:
            option: corresponds to option values under the power button,
                    see :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
            from_details: Whether or not to perform action from instance details page
        """
        if from_details:
            view = self.load_details(refresh=True)
        else:
            view = navigate_to(self, "All")
            entity = self.find_quadicon()
            entity.check()
        try:
            return not view.toolbar.power.item_enabled(option)
        except NoSuchElementException:
            return False

    def delete_from_provider(self):
        logger.info("Begin delete_from_provider")
        if self.provider.mgmt.does_vm_exist(self.name):
            try:
                if self.provider.mgmt.is_vm_suspended(self.name) and self.provider.type != 'azure':
                    logger.debug("Powering up VM %s to shut it down correctly on %s.",
                                self.name, self.provider.key)
                    self.provider.mgmt.start_vm(self.name)
                    self.provider.mgmt.wait_vm_steady(self.name)
                    self.provider.mgmt.stop_vm(self.name)
                    self.provider.mgmt.wait_vm_steady(self.name)
            except exceptions.ActionNotSupported:
                # Action is not supported on mgmt system. Simply continue
                pass
            # One more check (for the suspended one)
            if self.provider.mgmt.does_vm_exist(self.name):
                try:
                    logger.info("Mgmt System delete_vm")
                    return self.provider.mgmt.delete_vm(self.name)
                except exceptions.VMInstanceNotFound:
                    # Does not exist already
                    return True
        else:
            return True

    def create_on_provider(self, timeout=900, find_in_cfme=False, **kwargs):
        """Create the VM on the provider

        Args:
            timeout: Number of seconds to wait for the VM to appear in CFME
                     Will not wait at all, if set to 0 (Defaults to ``900``)
        """
        deploy_template(self.provider.key, self.name, self.template_name, **kwargs)
        if find_in_cfme:
            self.provider.refresh_provider_relationships()
            self.wait_to_appear(timeout=timeout, load_details=False)

    def does_vm_exist_on_provider(self):
        """Check if VM exists on provider itself"""
        return self.provider.mgmt.does_vm_exist(self.name)

    def set_retirement_date(self, when=None, offset=None, warn=None):
        """Overriding common method to use widgetastic views/widgets properly

        Args:
            when: :py:class:`datetime.datetime` object, when to retire (date in future)
            offset: :py:class:`dict` with months, weeks, days, hours keys. other keys ignored
            warn: When to warn, fills the select in the form in case the ``when`` is specified.

        Note: this should be moved up to the common VM class when infra+cloud+common are all WT

        If when and offset are both None, this removes retirement date

        Examples:
            # To set a specific retirement date 2 days from today
            two_days_later = datetime.date.today() + datetime.timedelta(days=2)
            vm.set_retirement_date(when=two_days_later)

            # To set a retirement offset 2 weeks from now
            vm.set_retirement_date(offset={weeks=2})

        Offset is dict to remove ambiguity between timedelta/datetime and months/weeks/days/hours
        timedelta supports creation with weeks, but not months
        timedelta supports days attr, but not weeks or months
        timedelta days attr will report a total summary, not the component that was passed to it
        For these reasons timedelta isn't appropriate for offset
        An enhancement to cfme.utils.timeutil extending timedelta would be great for making this a
        bit cleaner
        """
        new_retire = self.appliance.version >= "5.9"
        view = navigate_to(self, 'SetRetirement')
        fill_date = None
        fill_offset = None

        # explicit is/not None use here because of empty strings and dicts

        if when is not None and offset is not None:
            raise ValueError('set_retirement_date takes when or offset, but not both')
        if not new_retire and offset is not None:
            raise ValueError('Offset retirement only available in CFME 59z+ or miq-gaprindashvili')
        if when is not None and not isinstance(when, (datetime, date)):
            raise ValueError('when argument must be a datetime object')

        # due to major differences between the forms and their interaction, I'm splitting this
        # method into two major blocks, one for each version. As a result some patterns will be
        # repeated in both blocks
        # This will allow for making changes to one version or the other without strange
        # interaction in the logic

        # format the date
        # needs 4 digit year for fill
        # displayed 2 digit year for flash message
        if new_retire:
            # 59z/G-release retirement
            if when is not None and offset is None:
                # Specific datetime retire, H+M are 00:00 by default if just date passed
                fill_date = when.strftime('%m/%d/%Y %H:%M')  # 4 digit year
                msg_date = when.strftime('%m/%d/%y %H:%M UTC')  # two digit year and timestamp
                msg = 'Retirement date set to {}'.format(msg_date)
            elif when is None and offset is None:
                # clearing retirement date with empty string in textinput
                fill_date = ''
                msg = 'Retirement date removed'
            elif offset is not None:
                # retirement by offset
                fill_date = None
                fill_offset = {k: v for k, v in offset.items() if k in ['months',
                                                                        'weeks',
                                                                        'days',
                                                                        'hours']}
                # hack together an offset
                # timedelta can take weeks, but not months
                # copy and pop, only used to generate message, not used for form fill
                offset_copy = fill_offset.copy()
                if 'months' in offset_copy:
                    new_weeks = offset_copy.get('weeks', 0) + int(offset_copy.pop('months', 0)) * 4
                    offset_copy.update({'weeks': new_weeks})

                msg_date = datetime.utcnow() + timedelta(**offset_copy)
                msg = 'Retirement date set to {}'.format(msg_date.strftime('%m/%d/%y %H:%M UTC'))
            # TODO move into before_fill when no need to click away from datetime picker
            view.form.fill({
                'retirement_mode':
                    'Time Delay from Now' if fill_offset else 'Specific Date and Time'})
            view.flush_widget_cache()  # since retirement_date is conditional widget
            if fill_date is not None:  # specific check because of empty string
                # two part fill, widget seems to block warn selection when open
                changed_date = view.form.fill({
                    'retirement_date': {'datetime_select': fill_date}})
                view.title.click()  # close datetime widget
                changed_warn = view.form.fill({'retirement_warning': warn})
                changed = changed_date or changed_warn
            elif fill_offset:
                changed = view.form.fill({
                    'retirement_date': fill_offset, 'retirement_warning': warn})

        else:
            # 58z/euwe retirement
            if when:
                fill_date = when.strftime('%m/%d/%Y')  # 4 digit year
                msg_date = when.strftime('%m/%d/%y 00:00 UTC')  # two digit year and default 0 UTC
                msg = 'Retirement date set to {}'.format(msg_date)
            else:
                fill_date = None
                msg = 'Retirement date removed'
            if fill_date:
                changed = view.form.fill({'retirement_date': fill_date, 'retirement_warning': warn})
            else:
                if view.form.remove_date.is_displayed:
                    view.form.remove_date.click()
                    changed = True
                else:
                    # no date set, nothing to change
                    logger.info('Retirement date not set, cannot clear, canceling form')
                    changed = False

        # Form save and flash messages are the same between versions
        if changed:
            view.form.save.click()
        else:
            logger.info('No form changes for setting retirement, clicking cancel')
            view.form.cancel.click()
            msg = 'Set/remove retirement date was cancelled by the user'
        if self.DETAILS_VIEW_CLASS is not None:
            view = self.create_view(self.DETAILS_VIEW_CLASS)
            assert view.is_displayed
        view.flash.assert_success_message(msg)

    def equal_drift_results(self, drift_section, section, *indexes):
        """Compares drift analysis results of a row specified by it's title text.

        Args:
            drift_section (str): Title text of the row to compare
            section (str): Accordion section where the change happened
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default)

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            :py:class:`bool`
        """

        def _select_rows(indexes):
            for i in indexes:
                drift_history_view.history_table[i][0].click()

        # mark by indexes or mark all
        details_view = navigate_to(self, "Details")
        details_view.entities.relationships.click_at("Drift History")
        drift_history_view = self.create_view(DriftHistory)
        assert drift_history_view.is_displayed
        if indexes:
            _select_rows(indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            rows_number = len(list(drift_history_view.history_table.rows()))
            if rows_number > 10:
                _select_rows(range(10))
            else:
                _select_rows(range(rows_number))
        drift_history_view.analyze_button.click()
        drift_analysis_view = self.create_view(DriftAnalysis)
        assert drift_analysis_view.is_displayed
        drift_analysis_view.drift_sections.check_node(section)
        drift_analysis_view.apply_button.click()
        if not drift_analysis_view.toolbar.all_attributes.active:
            drift_analysis_view.toolbar.all_attributes.click()
        return drift_analysis_view.drift_analysis(drift_section).is_changed


class Template(BaseVM, _TemplateMixin):
    """A base class for all templates. The constructor is a bit different, it scraps template_name.
    """
    def __init__(self, name, provider, template_name=None):
        # template_name gets ignored because template does not have a template, logically.
        super(Template, self).__init__(name, provider, template_name=None)

    def does_template_exist_on_provider(self):
        """Check if template exists on provider itself"""
        return self.provider.mgmt.does_template_exist(self.name)
