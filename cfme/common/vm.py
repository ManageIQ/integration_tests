# -*- coding: utf-8 -*-
"""Module containing classes with common behaviour for both VMs and Instances of all types."""
from datetime import date
from functools import partial

from mgmtsystem import exceptions

from cfme import js
from cfme.exceptions import (
    VmOrInstanceNotFound, TemplateNotFound, OptionNotAvailable, UnknownProviderType)
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    AngularCalendarInput, AngularSelect, Form, InfoBlock, Input, Quadicon, Select, fill, flash,
    form_buttons, paginator, toolbar, PagedTable, SplitPagedTable, search, CheckboxTable,
    DriftGrid
)
import cfme.web_ui.toolbar as tb
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.timeutil import parsetime
from utils.update import Updateable
from utils.virtual_machines import deploy_template
from utils.wait import wait_for, TimedOutError

from . import PolicyProfileAssignable, Taggable, SummaryMixin

cfg_btn = partial(toolbar.select, "Configuration")
lcl_btn = partial(toolbar.select, "Lifecycle")
mon_btn = partial(toolbar.select, 'Monitoring')
pol_btn = partial(toolbar.select, "Policy")
pwr_btn = partial(toolbar.select, "Power")

retire_remove_button = "//span[@id='remove_button']/a/img|//a/img[contains(@src, '/clear')]"

set_ownership_form = Form(fields=[
    ('user_name', AngularSelect('user_name')),
    ('group_name', AngularSelect('group_name')),
    ('create_button', form_buttons.save),
    ('reset_button', form_buttons.reset),
    ('cancel_button', form_buttons.cancel)
])

drift_table = CheckboxTable("//th[normalize-space(.)='Timestamp']/ancestor::table[1]")


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


class BaseVM(Pretty, Updateable, PolicyProfileAssignable, Taggable, SummaryMixin, Navigatable):
    """Base VM and Template class that holds the largest common functionality between VMs,
    instances, templates and images.

    In order to inherit these, you have to implement the ``on_details`` method.
    """
    pretty_attrs = ['name', 'provider', 'template_name']

    # Forms
    edit_form = Form(
        fields=[
            ('custom_ident', Input("custom_1")),
            ('description_tarea', "//textarea[@id='description']"),
            ('parent_sel', {
                version.LOWEST: Select("//select[@name='chosen_parent']"),
                "5.5": AngularSelect("chosen_parent")}),
            ('child_sel', Select("//select[@id='kids_chosen']", multi=True)),
            ('vm_sel', Select("//select[@id='choices_chosen']", multi=True)),
            ('add_btn', "//img[@alt='Move selected VMs to left']"),
            ('remove_btn', "//img[@alt='Move selected VMs to right']"),
            ('remove_all_btn', "//img[@alt='Move all VMs to right']"),
        ])

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
    REMOVE_SELECTED = {'5.6': 'Remove selected items',
                       '5.6.2.2': 'Remove selected items from the VMDB',
                       '5.7': 'Remove selected items'}
    REMOVE_SINGLE = {'5.6': 'Remove Virtual Machine',
                     '5.6.2.2': 'Remove from the VMDB',
                     '5.7': 'Remove Virtual Machine'}
    RETIRE_DATE_FMT = {version.LOWEST: parsetime.american_date_only_format,
                       '5.7': parsetime.american_minutes_with_utc}

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

    @property
    def paged_table(self):
        _paged_table_template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
        return version.pick({
            version.LOWEST: SplitPagedTable(header_data=(_paged_table_template.format("xhdr"), 1),
                                            body_data=(_paged_table_template.format("objbox"), 0)),
            "5.5": PagedTable('//table'),
        })

    ###
    # Methods
    #
    def check_compliance(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        original_state = self.compliance_status
        cfg_btn("Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
        pol_btn("Check Compliance of Last Known Configuration", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
        wait_for(
            lambda: self.compliance_status != original_state,
            num_sec=timeout, delay=5, message="compliance of {} checked".format(self.name)
        )
        return self.compliant

    @property
    def compliance_status(self):
        """Returns the title of the compliance infoblock. The title contains datetime so it can be
        compared.

        Returns:
            :py:class:`NoneType` if no title is present (no compliance checks before), otherwise str
        """
        self.load_details(refresh=True)
        return InfoBlock("Compliance", "Status").title

    @property
    def compliant(self):
        """Check if the VM is compliant

        Returns:
            :py:class:`NoneType` if the VM was never verified, otherwise :py:class:`bool`
        """
        text = self.get_detail(properties=("Compliance", "Status")).strip().lower()
        if text == "never verified":
            return None
        elif text.startswith("non-compliant"):
            return False
        elif text.startswith("compliant"):
            return True
        else:
            raise ValueError("{} is not a known state for compliance".format(text))

    def delete(self, cancel=False, from_details=False):
        """Deletes the VM/Instance from the VMDB.

        Args:
            cancel: Whether to cancel the action in the alert.
            from_details: Whether to use the details view or list view.
        """

        if from_details:
            self.load_details(refresh=True)
            cfg_btn(self.REMOVE_SINGLE, invokes_alert=True)
        else:
            self.find_quadicon(mark=True)
            cfg_btn(self.REMOVE_SELECTED, invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    @property
    def exists(self):
        """Checks presence of the quadicon in the CFME."""
        try:
            self.find_quadicon()
            return True
        except VmOrInstanceNotFound:
            return False

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

    def find_quadicon(
            self, do_not_navigate=False, mark=False, refresh=True, from_any_provider=False,
            use_search=True):
        """Find and return a quadicon belonging to a specific vm

        Args:
            from_any_provider: Whether to look for it anywhere (root of the tree). Useful when
                looking up archived or orphaned VMs

        Returns: :py:class:`cfme.web_ui.Quadicon` instance
        Raises: VmOrInstanceNotFound
        """
        quadicon = Quadicon(self.name, self.quadicon_type)
        if not do_not_navigate:
            if from_any_provider:
                # TODO implement as navigate_to when cfme.infra.virtual_machines has destination
                navigate_to(self, 'All')
            elif self.is_vm:
                navigate_to(self, 'AllForProvider', use_resetter=False)
            else:
                navigate_to(self, 'AllForProvider', use_resetter=False)
            toolbar.select('Grid View')
        else:
            # Search requires navigation, we shouldn't use it then
            use_search = False
            if refresh:
                sel.refresh()
        if not paginator.page_controls_exist():
            if self.is_vm:
                raise VmOrInstanceNotFound("VM '{}' not found in UI!".format(self.name))
            else:
                raise TemplateNotFound("Template '{}' not found in UI!".format(self.name))

        paginator.results_per_page(1000)
        if use_search:
            try:
                if not search.has_quick_search_box():
                    # TODO rework search for archived/orphaned VMs
                    if self.is_vm:
                        navigate_to(self, 'AllForProvider', use_resetter=False)
                    else:
                        navigate_to(self, 'AllForProvider', use_resetter=False)
                search.normal_search(self.name)
            except Exception as e:
                logger.warning("Failed to use search: %s", str(e))
        for page in paginator.pages():
            if sel.is_displayed(quadicon, move_to=True):
                if mark:
                    sel.check(quadicon.checkbox())
                return quadicon
        else:
            raise VmOrInstanceNotFound("VM '{}' not found in UI!".format(self.name))

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
    def get_first_vm_title(cls, do_not_navigate=False, provider=None):
        """Get the title of first VM/Instance."""
        if not do_not_navigate:
            if provider is None:
                navigate_to(cls, 'All')
            else:
                provider.load_all_provider_vms()
        return Quadicon.get_first_quad_title()

    @property
    def last_analysed(self):
        """Returns the contents of the ``Last Analysed`` field in summary"""
        return self.get_detail(properties=('Lifecycle', 'Last Analyzed')).strip()

    def load_details(self, refresh=False):
        """Navigates to an VM's details page.

        Args:
            refresh: Refreshes the VM page if already there

        Raises:
            VmOrInstanceNotFound:
                When unable to find the VM passed
        """
        navigate_to(self, 'Details', use_resetter=False)
        if refresh:
            toolbar.refresh()

    def open_edit(self):
        """Loads up the edit page of the object."""
        self.load_details(refresh=True)
        cfg_btn(self.TO_OPEN_EDIT)

    def open_timelines(self):
        self.load_details(refresh=True)
        mon_btn("Timelines")

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

    def refresh_relationships(self, from_details=False, cancel=False):
        """Executes a refresh of relationships.

        Args:
            from_details: Whether or not to perform action from instance details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(mark=True)
        cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

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
            self.load_details(refresh=True)
        else:
            self.find_quadicon(mark=True)
        cfg_btn('Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_to_disappear(self, timeout=600, load_details=True):
        """Wait for a VM to disappear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
        """
        wait_for(
            lambda: self.exists,
            num_sec=timeout, delay=30, fail_func=sel.refresh, fail_condition=True,
            message="wait for vm to not exist")

    wait_for_delete = wait_to_disappear  # An alias for more fitting verbosity

    def wait_to_appear(self, timeout=600, load_details=True):
        """Wait for a VM to appear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
            from_details: when found, should it load the vm details
        """
        wait_for(
            lambda: self.exists,
            num_sec=timeout, delay=30, fail_func=sel.refresh,
            message="wait for vm to appear")
        if load_details:
            self.load_details()

    def set_ownership(self, user=None, group=None, click_cancel=False, click_reset=False):
        """Set ownership of the VM/Instance or Template/Image"""
        sel.click(self.find_quadicon(False, False, False, use_search=False))
        cfg_btn('Set Ownership')
        if click_reset:
            action = form_buttons.reset
            msg_assert = partial(
                flash.assert_message_match,
                'All changes have been reset'
            )
        elif click_cancel:
            action = form_buttons.cancel
            msg_assert = partial(
                flash.assert_success_message,
                'Set Ownership was cancelled by the user'
            )
        else:
            action = form_buttons.save
            msg_assert = partial(
                flash.assert_success_message,
                'Ownership saved for selected {}'.format(self.VM_TYPE)
            )
        fill(set_ownership_form, {'user_name': user, 'group_name': group},
             action=action)
        msg_assert()

    def unset_ownership(self):
        """Unset ownership of the VM/Instance or Template/Image"""
        # choose the vm code comes here
        sel.click(self.find_quadicon(False, False, False))
        cfg_btn('Set Ownership')
        fill(set_ownership_form, {'user_name': '<No Owner>',
            'group_name': 'EvmGroup-administrator'},
            action=form_buttons.save)
        flash.assert_success_message('Ownership saved for selected {}'.format(self.VM_TYPE))


def date_retire_element(fill_data):
    """We need to call this function that will mimic clicking the calendar, picking the date and
    the subsequent callbacks from the server"""
    # TODO: Move the code in the Calendar itself? I did not check other calendars
    if isinstance(fill_data, date):
        date_str = '{}/{}/{}'.format(fill_data.month, fill_data.day, fill_data.year)
    else:
        date_str = str(fill_data)
    sel.execute_script(
        js.update_retirement_date_function_script +
        "updateDate(arguments[0]);",
        date_str
    )


class VM(BaseVM):
    TO_RETIRE = None

    retire_form = Form(fields=[
        ('date_retire',
            AngularCalendarInput("retirement_date",
                                 "//label[contains(normalize-space(.), 'Retirement Date')]")),
        ('warn', AngularSelect('retirementWarning'))
    ])

    def retire(self):
        self.load_details(refresh=True)
        lcl_btn(self.TO_RETIRE, invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(
            'Retirement initiated for 1 VM and Instance from the {} Database'.format(version.pick({
                version.LOWEST: 'CFME',
                'upstream': 'ManageIQ'})))

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
        if (self.is_pwr_option_available_in_cfme(option=option, from_details=from_details)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel, check_present=True)
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
        self.load_details(refresh=True)
        wait_for(
            lambda: not toolbar.is_greyed('Monitoring', 'Utilization'),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=lambda: toolbar.refresh())

    def wait_for_vm_state_change(self, desired_state=None, timeout=300, from_details=False,
                                 with_relationship_refresh=True):
        """Wait for M to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: on, off, suspended... for available states, see
                           :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
            timeout: Specify amount of time (in seconds) to wait
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
                return 'currentstate-' + desired_state in self.find_quadicon().state

        return wait_for(
            _looking_for_state_change,
            num_sec=timeout,
            delay=30,
            fail_func=lambda: self.refresh_relationships(from_details=from_details) if
            with_relationship_refresh else None)

    def is_pwr_option_available_in_cfme(self, option, from_details=False):
        """Checks to see if a power option is available on the VM

        Args:
            option: corresponds to option values under the power button,
                    see :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
            from_details: Whether or not to perform action from instance details page
        """
        if from_details:
            self.load_details(refresh=True)
        else:
            self.find_quadicon(mark=True)
        try:
            return not toolbar.is_greyed('Power', option)
        except sel.NoSuchElementException:
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

    def set_retirement_date(self, when, warn=None):
        """Sets the retirement date for this Vm object.

        It incorporates some magic to make it work reliably since the retirement form is not very
        pretty and it can't be just "done".

        Args:
            when: When to retire. :py:class:`str` in format mm/dd/yyyy of
                :py:class:`datetime.datetime` or :py:class:`utils.timeutil.parsetime`.
            warn: When to warn, fills the select in the form in case the ``when`` is specified.
        """
        self.load_details()
        lcl_btn("Set Retirement Date")
        if callable(self.retire_form.date_retire):
            # It is the old functiton
            sel.wait_for_element("#miq_date_1")
        else:
            sel.wait_for_element(self.retire_form.date_retire)
        if when is None:
            try:
                wait_for(lambda: sel.is_displayed(retire_remove_button), num_sec=5, delay=0.2)
                sel.click(retire_remove_button)
                wait_for(lambda: not sel.is_displayed(retire_remove_button), num_sec=10, delay=0.2)
                sel.click(form_buttons.save)
            except TimedOutError:
                pass
        else:
            if sel.is_displayed(retire_remove_button):
                sel.click(retire_remove_button)
                wait_for(lambda: not sel.is_displayed(retire_remove_button), num_sec=15, delay=0.2)
            fill(self.retire_form.date_retire, when)
            wait_for(lambda: sel.is_displayed(retire_remove_button), num_sec=15, delay=0.2)
            if warn is not None:
                fill(self.retire_form.warn, warn)
            sel.click(form_buttons.save)

    def equal_drift_results(self, row_text, section, *indexes):
        """ Compares drift analysis results of a row specified by it's title text

        Args:
            row_text: Title text of the row to compare
            section: Accordion section where the change happened; this section will be activated
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default).

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            ``True`` if equal, ``False`` otherwise.
        """
        # mark by indexes or mark all
        self.load_details(refresh=True)
        sel.click(InfoBlock("Properties", "Drift History"))
        if indexes:
            drift_table.select_rows_by_indexes(*indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            if len(list(drift_table.rows())) > 10:
                drift_table.select_rows_by_indexes(*range(0, min(10, len)))
            else:
                drift_table.select_all()
        tb.select("Select up to 10 timestamps for Drift Analysis")

        # Make sure the section we need is active/open
        sec_loc_map = {
            'Properties': 'Properties',
            'Security': 'Security',
            'Configuration': 'Configuration',
            'My Company Tags': 'Categories'}
        sec_loc_template = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]" \
                           "//span[contains(@class, 'dynatree-checkbox')]"
        sec_checkbox_loc = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]" \
            "//span[contains(@class, 'dynatree-checkbox')]".format(sec_loc_map[section])
        sec_apply_btn = "//div[@id='accordion']/a[contains(normalize-space(text()), 'Apply')]"

        # Deselect other sections
        for other_section in sec_loc_map.keys():
            other_section_loc = sec_loc_template.format(sec_loc_map[other_section])
            other_section_classes = sel.get_attribute(other_section_loc + '/..', "class")
            if other_section != section and 'dynatree-partsel' in other_section_classes:
                # Element needs to be checked out if it has no dynatree-selected
                if 'dynatree-selected' not in other_section_classes:
                    sel.click(other_section_loc)
                sel.click(other_section_loc)

        # Activate the required section
        sel.click(sec_checkbox_loc)
        sel.click(sec_apply_btn)

        if not tb.is_active("All attributes"):
            tb.select("All attributes")
        drift_grid = DriftGrid()
        if any(drift_grid.cell_indicates_change(row_text, i) for i in range(0, len(indexes))):
            return False
        return True


class Template(BaseVM, _TemplateMixin):
    """A base class for all templates. The constructor is a bit different, it scraps template_name.
    """
    def __init__(self, name, provider, template_name=None):
        # template_name gets ignored because template does not have a template, logically.
        super(Template, self).__init__(name, provider, template_name=None)

    def does_vm_exist_on_provider(self):
        """Check if template exists on provider itself"""
        return self.provider.mgmt.does_template_exist(self.name)

    # For more logical writing of conditions.
    does_template_exist_on_provider = does_vm_exist_on_provider
