# -*- coding: utf-8 -*-
"""Module containing classes with common behaviour for both VMs and Instances of all types."""
import json
from datetime import date
from datetime import datetime
from datetime import timedelta

import attr
from cached_property import cached_property
from manageiq_client.filters import Q
from riggerlib import recursive_update

from cfme.base.login import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.common.vm_console import ConsoleMixin
from cfme.common.vm_views import DriftAnalysis
from cfme.common.vm_views import DriftHistory
from cfme.common.vm_views import VMPropertyDetailView
from cfme.exceptions import CFMEException
from cfme.exceptions import ItemNotFound
from cfme.exceptions import OptionNotAvailable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.services.requests import RequestsView
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.net import find_pingable
from cfme.utils.pretty import Pretty
from cfme.utils.rest import assert_response
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for


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


@attr.s
class BaseVM(
    BaseEntity,
    Pretty,
    Updateable,
    PolicyProfileAssignable,
    Taggable,
    ConsoleMixin,
    CustomButtonEventsMixin,
):
    """Base VM and Template class that holds the largest common functionality between VMs,
    instances, templates and images.

    In order to inherit these, you have to implement the ``on_details`` method.
    """
    pretty_attrs = ['name', 'provider', 'template_name']

    ###
    # To be set or implemented
    #
    ALL_LIST_LOCATION = None
    TO_OPEN_EDIT = None  # Name of the item in Configuration that puts you in the form
    QUADICON_TYPE = "vm"
    # Titles of the delete buttons in configuration
    REMOVE_SELECTED = 'Remove selected items from Inventory'
    REMOVE_SINGLE = 'Remove Virtual Machine from Inventory'
    RETIRE_DATE_FMT = parsetime.saved_report_title_format
    _param_name = ParamClassName('name')
    DETAILS_VIEW_CLASS = None

    ###
    # Shared behaviour
    #
    PROVISION_CANCEL = 'Add of new VM Provision Request was cancelled by the user'
    PROVISION_START = ('VM Provision Request was Submitted, you will be notified when your VMs '
                       'are ready')
    name = attr.ib()
    provider = attr.ib()

    def __new__(cls, *args, **kwargs):
        if cls in [BaseVM, VM, Template]:
            raise NotImplementedError('This class cannot be instantiated.')
        else:
            # magic {waves hands}
            return object.__new__(cls)

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
        view.toolbar.reload.click()
        return view.entities.summary("Compliance").get_text_of("Status")

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

    def delete(self, cancel=False, from_details=False):
        """Deletes the VM/Instance from the VMDB.

        Args:
            cancel: Whether to cancel the action in the alert.
            from_details: Whether to use the details view or list view.
        """

        if from_details:
            view = navigate_to(self, 'Details')
            view.toolbar.configuration.item_select(self.REMOVE_SINGLE,
                                                   handle_alert=not cancel)
        else:
            view = navigate_to(self.parent, 'All')
            self.find_quadicon().check()
            view.toolbar.configuration.item_select(self.REMOVE_SELECTED, handle_alert=not cancel)

    @property
    def ip_address(self):
        """Fetches IP Address of VM

        First looks to see if any of the mgmt ips returned by 'all_ips' are pingable
        Then defaults to whatever mgmt.ip returns
        """
        return find_pingable(self.mgmt)

    @property
    def all_ip_addresses(self):
        """Fetches all IP Addresses of a VM, pingable or otherwise."""
        # TODO: Implement sentaku for this property with ViaMGMT impl
        view = navigate_to(self, "Details", use_resetter=False)
        try:
            return view.entities.summary('Properties').get_text_of("IP Address")
        except NameError:
            # since some providers have plural 'Addresses'.
            return view.entities.summary('Properties').get_text_of("IP Addresses").split(", ")

    @property
    def mac_address(self):
        """Fetches MAC Address of VM"""
        # TODO: We should update this with wrapanapi method when it becomes available.
        view = navigate_to(self, "Details", use_resetter=False)
        try:
            return view.entities.summary('Properties').get_text_of("MAC Address")
        except NameError:
            # since some providers have plural 'Addresses'.
            return view.entities.summary('Properties').get_text_of("MAC Addresses")

    @property
    def is_retired(self):
        """Check retirement status of vm"""
        view = navigate_to(self, "Details", use_resetter=False)
        if view.entities.summary('Lifecycle').get_text_of('Retirement Date').lower() != 'never':
            try:
                retirement_state = VersionPicker({
                    LOWEST: 'Retirement state',
                    '5.10': 'Retirement State'
                })
                status = view.entities.summary('Lifecycle').get_text_of(retirement_state).lower()
                return status == 'retired'
            except NameError:
                return False
        else:
            return False

    def find_quadicon(self, from_any_provider=False, from_archived_all=False,
                      from_orphaned_all=False, use_search=True):
        """Find and return a quadicon belonging to a specific vm

        Args:
            from_any_provider: Whether to look for it anywhere (root of the tree). Useful when
                looking up archived or orphaned VMs

        Returns: entity of appropriate type
        Raises: ItemNotFound
        """
        # TODO(all): Refactor this method replace it with vm methods like get_state
        if from_any_provider:
            view = navigate_to(self.parent, 'All')
        elif from_archived_all:
            view = navigate_to(self.appliance.provider_based_collection(self.provider),
                               'ArchivedAll')
        elif from_orphaned_all:
            view = navigate_to(self.appliance.provider_based_collection(self.provider),
                               'OrphanedAll')
        else:
            view = navigate_to(self, 'AllForProvider', use_resetter=False)

        view.toolbar.view_selector.select('Grid View')
        try:
            return view.entities.get_entity(name=self.name, surf_pages=True, use_search=use_search)
        except ItemNotFound:
            raise ItemNotFound("VM '{}' not found in UI!".format(self.name))

    def open_console(self, console='VM Console', invokes_alert=None):
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
        """
        # TODO: implement vmrc vm console
        if console not in ['VM Console']:
            raise NotImplementedError('Not supported console type: {}'.format(console))

        view = navigate_to(self, 'Details')

        # Click console button given by type
        view.toolbar.access.item_select(console, handle_alert=invokes_alert)
        self.vm_console

    def open_details(self, properties=None):
        """Clicks on details infoblock"""
        view = navigate_to(self, 'Details')
        view.entities.summary(properties[0]).click_at(properties[1])
        return self.create_view(VMPropertyDetailView)

    @property
    def last_analysed(self):
        """Returns the contents of the ``Last Analysed`` field in summary"""
        view = navigate_to(self, "Details")
        view.toolbar.reload.click()
        return view.entities.summary("Lifecycle").get_text_of("Last Analyzed").strip()

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

        view.wait_displayed()
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
            view = navigate_to(self, 'Details', use_resetter=False)
        else:
            view = navigate_to(self.parent, 'All')
            self.find_quadicon(from_any_provider=from_any_provider).check()
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
                                               handle_alert=not cancel)

    @property
    def retirement_date(self):
        """Returns the retirement date of the selected machine, or 'Never'

        Returns:
            :py:class:`str` object
        """
        view = navigate_to(self, "Details")
        return view.entities.summary("Lifecycle").get_text_of("Retirement Date").strip()

    def smartstate_scan(self, cancel=False, from_details=False, wait_for_task_result=False):
        """Initiates fleecing from the UI.

        Args:
            cancel: Whether or not to cancel the refresh relationships action
            from_details: Whether or not to perform action from instance details page
        """
        if from_details:
            view = navigate_to(self, 'Details', use_resetter=False)
        else:
            view = navigate_to(self.parent, 'All')
            self.find_quadicon().check()
        view.toolbar.configuration.item_select('Perform SmartState Analysis',
                                               handle_alert=not cancel)
        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name='Scan from Vm {}'.format(self.name), tab='AllTasks')
            task.wait_for_finished()
            return task

    def wait_to_disappear(self, timeout=600):
        """Wait for a VM to disappear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
        """
        wait_for(
            lambda: self.exists,
            num_sec=timeout, delay=5, fail_func=self.browser.refresh, fail_condition=True,
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
            navigate_to(self, "Details", use_resetter=False)

    def set_ownership(self, user=None, group=None, click_cancel=False, click_reset=False):
        """Set instance ownership

        Args:
            user (User): user object for ownership
            group (Group): group object for ownership
            click_cancel (bool): Whether to cancel form submission
            click_reset (bool): Whether to reset form after filling
        """
        view = navigate_to(self, 'SetOwnership', wait_for_view=0)
        fill_result = view.form.fill({
            'user_name': user.name if user else None,
            'group_name': group.description if group else group})
        if not fill_result:
            view.form.cancel_button.click()
            view = self.create_view(navigator.get_class(self, 'Details').VIEW)
            view.flash.assert_success_message('Set Ownership was cancelled by the user')
            return

        # Only if the form changed
        if click_reset:
            view.form.reset_button.click()
            view.flash.assert_message('All changes have been reset', 'warning')
            # Cancel after reset
            assert view.form.is_displayed
            view.form.cancel_button.click()
        elif click_cancel:
            view.form.cancel_button.click()
            view.flash.assert_success_message('Set Ownership was cancelled by the user')
        else:
            # save the form
            view.form.save_button.click()
            view = self.create_view(navigator.get_class(self, 'Details').VIEW)
            view.flash.assert_success_message('Ownership saved for selected {}'
                                              .format(self.VM_TYPE))

    def unset_ownership(self):
        """Remove user ownership and return group to EvmGroup-Administrator"""
        view = navigate_to(self, 'SetOwnership', wait_for_view=0)
        fill_result = view.form.fill({
            'user_name': '<No Owner>', 'group_name': 'EvmGroup-administrator'
        })
        if fill_result:
            view.form.save_button.click()
            msg = 'Ownership saved for selected {}'.format(self.VM_TYPE)
        else:
            view.form.cancel_button.click()
            logger.warning('No change during unset_ownership')
            msg = 'Set Ownership was cancelled by the user'

        view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        view.flash.assert_success_message(msg)

    def rename(self, new_vm_name, cancel=False, reset=False):
        """Rename the VM

        Args:
            new_vm_name: object for renaming vm
            cancel (bool): Whether to cancel form submission
            reset (bool): Whether to reset form after filling
        """
        view = navigate_to(self, 'Rename')
        changed = view.vm_name.fill(new_vm_name)
        if changed:
            if reset:
                view.reset_button.click()
                view.flash.assert_no_error()
                view.cancel_button.click()
            else:
                # save the form
                view.save_button.click()
                view.flash.assert_no_error()
                self.name = new_vm_name
                return self
        if cancel:
            view.cancel_button.click()
            view.flash.assert_no_error()

    @property
    def rest_api_entity(self):
        return self.appliance.rest_api.collections.vms.filter(
            Q("name", "=", self.name)
            & Q("ems_id", "=", self.provider.rest_api_entity.id)
        ).resources[0]

    def wait_for_power_state_change_rest(self, desired_state, timeout=1200, delay=45):
        """Wait for a VM/Instance power state to change to a desired state.

        Args:
            desired_state: A string indicating the desired state
            timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        """
        return wait_for(
            lambda: self.rest_api_entity.power_state == desired_state,
            fail_func=self.rest_api_entity.reload,
            num_sec=timeout,
            delay=delay,
            handle_exception=True,
            message=f"Waiting for VM/Instance power state to change to {desired_state}"
        ).out


@attr.s
class BaseVMCollection(BaseCollection):
    ENTITY = BaseVM

    def instantiate(self, name, provider, template_name=None):
        """Factory class method that determines the correct subclass for given provider.

        For reference how does that work, refer to the entrypoints in the setup.py

        Args:
            name: Name of the VM/Instance as it appears in the UI
            provider: The provider object (not the string!)
            template_name: Source template name. Useful when the VM/Instance does not exist and you
                want to create it.
        """
        # When this collection is filtered and used for instantiation, the ENTITY attribute
        # points to BaseVM instead of a specific VM type ENTITY class
        # For this reason we don't use self.ENTITY, but instead lookup the entity class
        # through the provider's attributes

        if isinstance(self, TemplateCollection):
            # This is a Template derived class, not a VM
            return provider.template_class.from_collection(self, name, provider)
        else:
            return provider.vm_class.from_collection(self, name, provider, template_name)

    def create(self, vm_name, provider, form_values=None, cancel=False, check_existing=False,
               find_in_cfme=False, wait=True, request_description=None, auto_approve=False,
               override=False):
        """Provisions an vm/instance with the given properties through CFME

        Args:
            vm_name: the vm/instance's name
            provider: provider object
            form_values: dictionary of form values for provisioning, structured into tabs
            cancel: boolean, whether or not to cancel form filling
            check_existing: verify if such vm_name exists
            find_in_cfme: verify that vm was created and appeared in CFME
            wait: wait for vm provision request end
            request_description: request description that test needs to search in request table.
            auto_approve: if true the request is approved before waiting for completion.
            override: To override any failure related exception

        Note:
            Calling create on a sub-class of instance will generate the properly formatted
            dictionary when the correct fields are supplied.
        """
        vm = self.instantiate(vm_name, provider)
        if check_existing and vm.exists:
            return vm
        if not provider.is_refreshed():
            provider.refresh_provider_relationships()
            wait_for(provider.is_refreshed, func_kwargs={'refresh_delta': 10}, timeout=600)
        if not form_values:
            form_values = vm.vm_default_args
        else:
            inst_args = vm.vm_default_args
            form_values = recursive_update(inst_args, form_values)
        env = form_values.get('environment') or {}
        if env.get('automatic_placement'):
            form_values['environment'] = {'automatic_placement': True}
        form_values.update({'provider_name': provider.name})
        if not form_values.get('template_name'):
            template_name = (provider.data.get('provisioning').get('image', {}).get('name') or
                             provider.data.get('provisioning').get('template'))
            vm.template_name = template_name
            form_values.update({'template_name': template_name})
        view = navigate_to(self, 'Provision')
        view.form.fill(form_values)

        if cancel:
            view.form.cancel_button.click()
            view = self.browser.create_view(BaseLoggedInPage)
            view.flash.assert_success_message(self.ENTITY.PROVISION_CANCEL)
            view.flash.assert_no_error()
        else:
            view.form.submit_button.click()

            view = vm.appliance.browser.create_view(RequestsView)
            if not BZ(1608967, forced_streams=['5.10']).blocks:
                wait_for(lambda: view.flash.messages, fail_condition=[], timeout=10, delay=2,
                        message='wait for Flash Success')
            # This flash message is not flashed in 5.10.
            if self.appliance.version < 5.10:
                wait_for(lambda: view.flash.messages, fail_condition=[], timeout=10, delay=2,
                         message='wait for Flash Success')
            view.flash.assert_no_error()
            if wait:
                if request_description is None:
                    request_description = 'Provision from [{}] to [{}]'.format(
                        form_values.get('template_name'), vm.name)
                provision_request = vm.appliance.collections.requests.instantiate(
                    request_description)
                logger.info('Waiting for cfme provision request for vm %s', vm.name)
                if auto_approve:
                    provision_request.approve_request(method='ui', reason="Approved")
                provision_request.wait_for_request(method='ui', num_sec=1200)
                if provision_request.is_succeeded(method='ui'):
                    logger.info('Waiting for vm %s to appear on provider %s', vm.name,
                                provider.key)
                    wait_for(provider.mgmt.does_vm_exist, [vm.name],
                             handle_exception=True, num_sec=600)
                elif override:
                    logger.info('Overriding exception to check failure condition.')
                else:
                    raise Exception(
                        "Provisioning vm {} failed with: {}"
                        .format(vm.name, provision_request.row.last_message.text)
                    )
        if find_in_cfme:
            vm.wait_to_appear(timeout=800)

        return vm

    def create_rest(self, vm_name, provider, form_values=None, check_existing=False):
        """Provisions a VM/Instance with the default self.vm_default_args_rest.

        self.vm_default_args_rest may be overridden by form_values.
        For more details about rest attributes please check:
        https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.6/html-single/
        red_hat_cloudforms_rest_api/index#provision-request-supported-attributes or
        http://manageiq.org/docs/reference/fine/api/appendices/provision_attributes
        NOTE: placement_auto defaults to True for requests made from the API or CloudForms Automate.
        Args:
            vm_name: vm name
            provider: provider object
            form_values: overrides default provision arguments or extends it.
            check_existing: cancel creation if VM exists
        Return: Instance object
        """
        vm = self.instantiate(vm_name, provider)
        if check_existing and vm.exists:
            return vm
        else:
            if not provider.is_refreshed():
                provider.refresh_provider_relationships()
                wait_for(provider.is_refreshed, func_kwargs={'refresh_delta': 10}, timeout=600)

            if not form_values:
                form_values = vm.vm_default_args_rest
            else:
                inst_args = vm.vm_default_args_rest
                form_values = recursive_update(inst_args, form_values)
            response = self.appliance.rest_api.collections.provision_requests.action.create(
                **form_values)[0]
            assert_response(self.appliance)

            provision_request = vm.appliance.collections.requests.instantiate(
                description=response.description)

            provision_request.wait_for_request(num_sec=900)
            if provision_request.is_succeeded():
                wait_for(lambda: provider.mgmt.does_vm_exist(vm.name), num_sec=1000, delay=5,
                         message="VM {} becomes visible".format(vm.name))
            else:
                logger.error("Provisioning failed with the message {}".
                            format(provision_request.rest.message))
                raise CFMEException(provision_request.rest.message)
        return vm


@attr.s
class VM(BaseVM):
    template_name = attr.ib(default=None)

    TO_RETIRE = None

    # May be overriden by implementors of BaseVM
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_PAUSED = "paused"
    STATE_SUSPENDED = "suspended"

    @cached_property
    def mgmt(self):
        """
        Returns the wrapanapi VM entity object to manipulate this VM directly via the provider API
        """
        return self.provider.mgmt.get_vm(self.name)

    @property
    def exists_on_provider(self):
        return self.provider.mgmt.does_vm_exist(self.name)

    def retire(self):
        view = navigate_to(self, 'Details', use_resetter=False)
        view.toolbar.reload.click()
        view.toolbar.lifecycle.item_select(self.TO_RETIRE, handle_alert=True)
        view.flash.assert_no_error()

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
            view = navigate_to(self, 'Details', use_resetter=False)
        else:
            view = navigate_to(self.parent, 'All')

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
        view = navigate_to(self, 'Details', use_resetter=False)
        view.toolbar.reload.click()
        wait_for(
            lambda: view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=view.toolbar.reload.click)

    def capture_historical_data(self, interval="hourly", back="6.days"):
        """Capture historical utilization data for this VM/Instance

        Args:
            interval: Data interval (hourly/ daily)
            back: back time interval from which you want data
        """
        ret = self.appliance.ssh_client.run_rails_command(
            "'vm = Vm.where(:ems_id => {prov_id}).where(:name => {vm_name})[0];\
            vm.perf_capture({interval}, {back}.ago.utc, Time.now.utc)'".format(
                prov_id=self.provider.id,
                vm_name=json.dumps(self.name),
                interval=json.dumps(interval),
                back=back,
            )
        )
        return ret.success

    def wait_for_vm_state_change(self, desired_state=None, timeout=300, from_details=False,
                                 with_relationship_refresh=True, from_any_provider=False):
        """Wait for VM to come to desired state in the UI.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: on, off, suspended... for available states, see
                           :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
            timeout: Specify amount of time (in seconds) to wait
            from_any_provider: Archived/Orphaned vms need this
        Raises:
            TimedOutError:
                When instance does not come up to desired state in specified period of time.
            ItemNotFound:
                When unable to find the instance passed
        """

        def _looking_for_state_change():
            if from_details:
                view = navigate_to(self, "Details", use_resetter=False)
                view.toolbar.reload.click()
                current_state = view.entities.summary("Power Management").get_text_of("Power State")
                return current_state == desired_state
            else:
                return self.find_quadicon(
                    from_any_provider=from_any_provider).data['state'] == desired_state

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
            view = navigate_to(self, 'Details', use_resetter=False)
            view.toolbar.reload.click()
        else:
            view = navigate_to(self.parent, "All")
            entity = self.find_quadicon()
            entity.check()
        if view.toolbar.power.has_item(option):
            return view.toolbar.power.item_enabled(option)
        else:
            return False

    def create_on_provider(self, timeout=900, find_in_cfme=False, delete_on_failure=True, **kwargs):
        """Create the VM on the provider via MgmtSystem. `deploy_template` handles errors during
        VM provision on MgmtSystem sideNS deletes VM if provisioned incorrectly

        Args:
            timeout: Number of seconds to wait for the VM to appear in CFME
                     Will not wait at all, if set to 0 (Defaults to ``900``)
            find_in_cfme: Verifies that VM exists in CFME UI
            delete_on_failure: Attempts to remove VM on UI navigation failure
        """
        vm = deploy_template(self.provider.key, self.name, self.template_name, **kwargs)
        try:
            if find_in_cfme:
                self.wait_to_appear(timeout=timeout, load_details=False)
        except Exception:
            logger.warning("Couldn't find VM or Instance '%s' in CFME", self.name)
            if delete_on_failure:
                logger.info("Removing VM or Instance from mgmt system")
                self.cleanup_on_provider()
            raise
        return vm

    def cleanup_on_provider(self):
        """Clean up entity on the provider if it has been created on the provider

        Helper method to avoid NotFoundError's during test case tear down.
        """
        if self.exists_on_provider:
            self.mgmt.cleanup()
        else:
            logger.debug('cleanup_on_provider: entity "%s" does not exist', self.name)

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
        view = navigate_to(self, 'SetRetirement')
        fill_date = None
        fill_offset = None

        # explicit is/not None use here because of empty strings and dicts

        if when is not None and offset is not None:
            raise ValueError('set_retirement_date takes when or offset, but not both')
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
        # 59z/G-release retirement
        changed = False  # just in case it isn't set in logic
        if when is not None and offset is None:
            # Specific datetime retire, H+M are 00:00 by default if just date passed
            fill_date = when.strftime('%m/%d/%Y %H:%M')  # 4 digit year
            msg_date = when.strftime('%m/%d/%y %H:%M UTC')  # two digit year and timestamp
            msg = 'Retirement date set to {}'.format(msg_date)
        elif when is None and offset is None:
            # clearing retirement date with space in textinput,
            # using space here as with empty string calendar input is not cleared correctly
            fill_date = ' '
            msg = 'Retirement date removed'
        elif offset is not None:
            # retirement by offset
            fill_date = None
            fill_offset = {k: v
                           for k, v in offset.items()
                           if k in ['months', 'weeks', 'days', 'hours']}
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

        # Form save and flash messages are the same between versions
        if changed:
            view.form.save.click()
        else:
            logger.info('No form changes for setting retirement, clicking cancel')
            view.form.cancel.click()
            msg = 'Set/remove retirement date was cancelled by the user'
        if self.DETAILS_VIEW_CLASS is not None:
            view = self.create_view(self.DETAILS_VIEW_CLASS, wait='5s')
        view.flash.assert_success_message(msg)

    def equal_drift_results(self, drift_section, section, *indexes):
        """Compares drift analysis results of a row specified by it's title text.

        Args:
            drift_section (str): Title text of the row to compare
            section (str): Accordion section where the change happened
            indexes: Indexes of results to compare starting with 1 for first row (latest result).
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
        details_view.entities.summary("Relationships").click_at("Drift History")
        drift_history_view = self.create_view(DriftHistory, wait='10s')
        if indexes:
            _select_rows(indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            rows_number = len(list(drift_history_view.history_table.rows()))
            if rows_number > 10:
                _select_rows(list(range(10)))
            else:
                _select_rows(list(range(rows_number)))
        drift_history_view.analyze_button.click()
        drift_analysis_view = self.create_view(DriftAnalysis, wait='10s')
        drift_analysis_view.drift_sections.check_node(section)
        drift_analysis_view.apply_button.click()
        if not drift_analysis_view.toolbar.all_attributes.active:
            drift_analysis_view.toolbar.all_attributes.click()
        return drift_analysis_view.drift_analysis.is_changed(drift_section)


@attr.s
class VMCollection(BaseVMCollection):
    ENTITY = VM


@attr.s
class Template(BaseVM, _TemplateMixin):
    """A base class for all templates.
    """
    @cached_property
    def mgmt(self):
        """Holds wrapanapi template entity object for this template."""
        return self.provider.mgmt.get_template(self.name)

    @property
    def exists_on_provider(self):
        return self.provider.mgmt.does_template_exist(self.name)


@attr.s
class TemplateCollection(BaseVMCollection):
    ENTITY = Template
