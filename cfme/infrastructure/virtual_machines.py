"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""


import ui_navigate as nav
from cfme.exceptions import NoVmFound, NoOptionAvailable, ParmRequired
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Region, Quadicon, CheckboxTree, Tree, paginator, accordion, toolbar
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from utils.log import logger
from utils.virtual_machines import deploy_template
from utils.wait import wait_for
from utils import version


details_page = Region(infoblock_type='detail')

cfg_btn = partial(toolbar.select, 'Configuration')
pol_btn = partial(toolbar.select, 'Policy')
lcl_btn = partial(toolbar.select, 'Lifecycle')
mon_btn = partial(toolbar.select, 'Monitoring')
pwr_btn = partial(toolbar.select, 'Power')

visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

manage_policies_tree = CheckboxTree(
    version.pick({
        "default": "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    })
)

manage_policies_page = Region(
    locators={
        'save_button': "//div[@id='buttons_on']//img[@alt='Save Changes']",
    })

snapshot_form = Form(
    fields=[
        ('name', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('descrition', "//*[@id='default_userid']"),
        ('snapshot_memory', "//*[@id='default_password']"),
        ('create_button', "//input[@name='create']"),
        ('cancel_button', "//input[@name='cancel']")
    ])


def accordion_fn(acc, tree):
    def f(_):
        accordion.click(acc)
        visible_tree.click_path(tree)
    return f


nav.add_branch(
    'infrastructure_virtual_machines',
    {
        "infra_vm_and_templates":
        [
            accordion_fn("VMs & Templates", "All VMs & Templates"),
            {
                "vm_templates_provider_branch":
                [
                    lambda ctx: visible_tree.click_path(ctx["provider_name"]),
                    {
                        "datacenter_branch":
                        [
                            lambda ctx: visible_tree.click_path(ctx["datacenter_name"]),
                            {
                                "infra_vm_obj": lambda ctx: visible_tree.click_path(ctx["vm_name"]),
                            }
                        ],
                    }
                ],

                "vm_templates_archived_branch":
                [
                    lambda ctx: visible_tree.click_path('Archived'),
                    {
                        "infra_archive_obj":
                        lambda ctx: visible_tree.click_path(ctx["archive_name"]),
                    }
                ],

                "vm_templates_orphaned_branch":
                [
                    lambda ctx: visible_tree.click_path('Orphaned'),
                    {
                        "infra_orphan_obj": lambda ctx: visible_tree.click_path(ctx["orphan_name"]),
                    }
                ],
            }
        ],

        "infra_vms":
        [
            lambda _: accordion.click("VMs"),
            {
                "infra_vms_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "infra_vms_filter": lambda ctx: visible_tree.click_path(ctx["filter_name"]),
                    }
                ],
            }
        ],

        "infra_templates":
        [
            lambda _: accordion.click("Templates"),
            {
                "infra_templates_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "infra_templates_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"]),
                    }
                ],
            }
        ],
    }
)


class Vm():

    # POWER CONTROL OPTIONS
    SUSPEND = "Suspend"
    POWER_ON = "Power On"
    POWER_OFF = "Power Off"
    GUEST_RESTART = "Restart Guest"
    GUEST_SHUTDOWN = "Shutdown Guest"
    RESET = "Reset"
    # POWER STATE
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"

    def __init__(self, name, provider_crud, template_name=None):
        self.name = name
        self.template_name = template_name
        self.provider_crud = provider_crud

    def create_on_provider(self):
        """Create the VM on the provider"""
        deploy_template(self.provider_crud, self.name, self.template_name)

    def create(self, timeout_in_minutes=15):
        """Create on the provider but get CFME to qucikly find it"""
        self.create_on_provider()
        self.provider_crud.refresh_provider_relationships()
        self.wait_for_vm_to_appear(timeout_in_minutes=timeout_in_minutes, load_details=False)

    def load_details(self, refresh=False):
        """Navigates to a VM's details page.

        Args:
            refresh: Refreshes the vm page if already there

        Raises:
            NoVmFound:
                When unable to find the VM passed
        """
        if not self.on_details():
            logger.debug("load_vm_details: not on details already")
            sel.click(self.find_quadicon())
        else:
            if refresh:
                toolbar.refresh()

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper vm details page.

        Args:
            vm_name: VM name that you are looking for.
            force: If its not on the right page, load it.
            provider_name: name of provider the vm resides on.
            datacenter_name: When passed with provider_name, allows navigation through tree
                when navigating to the vm
        """
        locator = ("//div[@class='dhtmlxInfoBarLabel' and contains(. , 'VM and Instance \"%s\"')]" %
            self.name)
        if not sel.is_displayed(locator):
            if not force:
                return False
            else:
                self.load_details()
                return True

        text = sel.text(locator).encode("utf-8")
        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        import re
        m = re.search(pattern, text)

        if not force:
            return self.name == m.group().replace('"', '')
        else:
            if self.name != m.group().replace('"', ''):
                self.load_vm_details()
            else:
                return False

    def find_quadicon(self, do_not_navigate=False, mark=False, refresh=True):
        """Find and return a quadicon belonging to a specific vm

        Args:
            vm: Host name as displayed at the quadicon
        Returns: :py:class:`cfme.web_ui.Quadicon` instance
        """
        if not do_not_navigate:
            self.provider_crud.load_all_provider_vms()
            toolbar.set_vms_grid_view()
        if refresh:
            sel.refresh()
        for page in paginator.pages():
            quadicon = Quadicon(self.name, "vm")
            if sel.is_displayed(quadicon):
                if mark:
                    sel.click(quadicon.checkbox())
                return quadicon
        else:
            raise NoVmFound("VM '{}' not found in UI!".format(self.name))

    def does_vm_exist_on_provider(self):
        """Check if VM exists on provider itself"""
        return self.provider_crud.get_mgmt_system().does_vm_exist(self.name)

    def does_vm_exist_in_cfme(self):
        """A function to tell you if a VM exists or not.
        """
        try:
            self.find_quadicon()
            return True
        except NoVmFound:
            return False

    def _method_helper(self, from_details=False):
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(mark=True)

    def remove_from_cfme(self, cancel=True, from_details=False):
        """Removes a VM from CFME VMDB

        Args:
            cancel: Whether to cancel the deletion, defaults to True
            from_details: whether to delete from the details page (vm_names length must be one)
        """
        self._method_helper(self, from_details)
        if from_details:
            cfg_btn('Remove from the VMDB', invokes_alert=True)
        else:
            cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def delete_from_provider(self):
        provider_mgmt = self.provider_crud.get_mgmt_system()
        if provider_mgmt.does_vm_exist(self.name):
            if provider_mgmt.is_vm_suspended(self.name):
                logger.debug("Powering up VM %s to shut it down correctly on %s." %
                    (self.name, self.provider_crud.key))
                provider_mgmt.start_vm(self.name)
            return self.provider_crud.get_mgmt_system().delete_vm(self.name)
        else:
            return True

    def get_detail(self, properties=None):
        """Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific vm.

        Args:
            properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns:
            A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        return details_page.infoblock.text(*properties)

    def power_control_from_provider(self, option=None):
        """Power control a vm from the provider

        Args:
            option: power control action to take against vm

        Raises:
            NoOptionAvailable: option parm must have proper value
            ParmRequired: option parm is required
        """
        self._power_helper(option=option)
        if option == Vm.POWER_ON:
            self.provider_crud.get_mgmt_system().start_vm(self.name)
        elif option == Vm.POWER_OFF:
            self.provider_crud.get_mgmt_system().stop_vm(self.name)
        elif option == Vm.SUSPEND:
            self.provider_crud.get_mgmt_system().suspend_vm(self.name)
        # elif reset:
        # elif shutdown:
        else:
            raise NoOptionAvailable(option + " is not a supported action")

    def _power_helper(self, option=None, from_details=False):
        if option is None:
            raise ParmRequired("option is a required parm")
        self._method_helper(from_details=from_details)

    def power_control_from_cfme(self, cancel=True, from_details=False, option=None):
        """Power controls a VM from within CFME

        Args:
            from_details: Whether or not to perform action from vm details page
            option: corresponds to option values under the power button
            cancel: Whether or not to cancel the power operation on confirmation
        """
        if (self.is_pwr_option_available_in_cfme(option=option, from_details=from_details)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)
                logger.info(
                    "Power control action of vm %s, option %s, cancel %s exectuted" %
                    (self.name, option, str(cancel)))
        else:
            raise NoOptionAvailable(option + " is not a visible or enabled")

    def is_pwr_option_available_in_cfme(self, from_details=False, option=None):
        """Checks to see if a power option is available on the VM

        Args:
            from_details: Whether or not to perform action from vm details page
            option: corresponds to option values under the power button, preferred approach
                is to use Vm option constansts
        """
        self._power_helper(option=option, from_details=from_details)
        try:
            return not toolbar.is_greyed('Power', option)
        except NoSuchElementException:
            return False

    def refresh_relationships(self, from_details=False, cancel=False):
        """Executes a refresh relationships action against a list of VMs.

        Args:
            from_details: Whether or not to perform action from vm details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(mark=True)
        cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    # def smartstate_scan(self, cancel=True, from_details=False):
    #     self._method_helper(self, from_details)
    #     cfg_btn('Perform SmartState Analysis', invokes_alert=True)

    # def edit_tags(self, cancel=True, from_details=False):
    #     raise NotImplementedError('edit tags is not implemented.')

    # def _nav_to_snapshot_mgmt(self):
    #     locator = ("//div[@class='dhtmlxInfoBarLabel' and " +
    #         "contains(. , '\"Snapshots\" for Virtual Machine \"%s\"' % self.name) ]")
    #     if not sel.is_displayed(locator):
    #         self.load_details()
    #         sel.click(details_page.infoblock.element("Properties", "Snapshots"))

    # def create_snapshot(self, name, description, snapshot_memory=False):
    #     self._nav_to_snapshot_mgmt()
    #     raise NotImplementedError('snapshot mgmt is not implemented.')

    # def remove_selected_snapshot(self, name):
    #     self._nav_to_snapshot_mgmt()
    #     raise NotImplementedError('snapshot mgmt is not implemented.')

    # def remove_all_snapshots(self):
    #     self._nav_to_snapshot_mgmt()
    #     raise NotImplementedError('snapshot mgmt is not implemented.')

    # def list_snapshots(self):
    #     self._nav_to_snapshot_mgmt()
    #     if sel.is_displayed("//strong[contains(, 'has no snapshots')"):
    #         return 0
    #     else:
    #         pass
    #     raise NotImplementedError('snapshot mgmt is not implemented.')

    # def revert_to_snapshot(self, name):
    #     self._nav_to_snapshot_mgmt()
    #     raise NotImplementedError('snapshot mgmt is not implemented.')

    def wait_for_vm_state_change(
            self, desired_state=None, timeout_in_minutes=5, from_details=False):
        """Wait for VM to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: on, off, suspended... corresponds to values in cfme, preferred approach
                is to use Vm.STATE_* constansts
            timeout_in_minutes: Specify amount of time to wait
        Raises:
            TimedOutError:
                When VM does not come up to desired state in specified period of time.
            NoVmFound:
                When unable to find the VM passed
        """
        def _looking_for_state_change():
            if from_details:
                self.load_details(refresh=True)
                detail_t = "Power Management", "Power State"
                return self.get_detail(properties=detail_t) == desired_state
            else:
                return self.find_quadicon().state == 'currentstate-' + desired_state
        return wait_for(_looking_for_state_change, num_sec=timeout_in_minutes * 60, delay=30)

    def wait_for_vm_to_appear(self, timeout_in_minutes=10, load_details=True):
        """Wait for a VM to appear within CFME

        Args:
            timeout_in_minutes: time to wait for it to appear
            from_details: when found, should it load the vm details
        """
        wait_for(self.does_vm_exist_in_cfme, num_sec=timeout_in_minutes * 60, delay=30)
        if load_details:
            self.load_details()


def _method_setup(vm_names, provider_crud=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]

    if provider_crud:
        provider_crud.load_all_provider_vms()
    else:
        sel.force_navigate('infra_vms')
    # TODO: add a paginator call to display 1000
    for vm_name in vm_names:
        sel.click(Quadicon(vm_name, 'vm').checkbox())


def find_quadicon(vm_name, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific vm

    Args:
        vm: vm name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    for page in paginator.pages():
        quadicon = Quadicon(vm_name, "vm")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
        raise NoVmFound("VM '{}' not found in UI!".format(vm_name))


def remove(vm_names, cancel=True, provider_crud=None):
    """Removes multiple VMs from CFME VMDB

    Args:
        vm_names: List of VMs to interact with
        cancel: Whether to cancel the deletion, defaults to True
        provider_crud: provider object where vm resides on (optional)
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def wait_for_vm_state_change(vm_name, desired_state, timeout_in_minutes=300, provider_crud=None):
    """Wait for VM to come to desired state.

    This function waits just the needed amount of time thanks to wait_for.

    Args:
        vm_name: Displayed name of the VM
        desired_state: 'on' or 'off'
        timeout_in_minutes: Specify amount of time to wait until TimedOutError is raised in minutes.
        provider_crud: provider object where vm resides on (optional)
    """
    def _looking_for_state_change():
        toolbar.refresh()
        find_quadicon(vm_name, do_not_navigate=False).state == 'currentstate-' + desired_state

    _method_setup(vm_name, provider_crud)
    return wait_for(_looking_for_state_change, num_sec=timeout_in_minutes * 60)


def is_pwr_option_visible(vm_names, provider_crud=None, option=None):
    """Returns whether a particular power option is visible.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed, only one VM can
            be passed in the list.
        provider_crud: provider object where vm resides on (optional)
        option: Power option param.

    Raises:
        ParmRequired:
            When no power option is passed
    """
    if option is None:
        raise ParmRequired("power option parm is required")
    _method_setup(vm_names, provider_crud)
    try:
        toolbar.is_greyed('Power', option)
        return True
    except NoSuchElementException:
        return False


def is_pwr_option_enabled(vm_names, provider_crud=None, option=None):
    """Returns whether a particular power option is enabled.

    Args:
        vm_names: List of VMs to interact with
        provider_crud:
        option: Power option param.

    Raises:
        NoOptionAvailable:
            When unable to find the power option passed
        ParmRequired:
            When no power option is passed
    """
    if option is None:
        raise ParmRequired("power option parm is required")
    _method_setup(vm_names, provider_crud)
    try:
        return not toolbar.is_greyed('Power', option)
    except NoSuchElementException:
        raise NoOptionAvailable("No such power option (" + str(option) + ") is available")


def do_power_control(vm_names, provider_crud=None, option=None, cancel=True):
    """Executes a power option against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the power control action
        option: Power option param.

    Raises:
        ParmRequired:
            When no power option is passed
    """

    if option is None:
        raise ParmRequired("power option parm is required")
    _method_setup(vm_names, provider_crud)

    if (is_pwr_option_visible(vm_names, provider_crud=provider_crud, option=option) and
            is_pwr_option_enabled(vm_names, provider_crud=provider_crud, option=option)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)


def refresh_relationships(vm_names, provider_crud=None, cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the refresh relationships action
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def perform_smartstate_analysis(vm_names, provider_crud=None, cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the refresh relationships action
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Perform SmartState Analysis', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def get_all_vms(do_not_navigate=False):
    """Returns list of all vms"""
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    vms = set([])
    try:
        for page in paginator.pages():
            for title in sel.elements(
                    "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')" +
                    " or contains(@href, '/show/')]"):  # for provider specific vm/template page
                vms.add(sel.get_attribute(title, "title"))
        return vms
    except NoSuchElementException:
        return set([])


def _assign_unassign_policy_profiles(vm_name, assign, *policy_profile_names, **kwargs):
    """DRY function for managing policy profiles.

    See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

    Args:
        vm_name: Name of the VM.
        assign: Wheter to assign or unassign.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    _method_setup(vm_name, **kwargs)
    toolbar.select("Policy", "Manage Policies")
    for policy_profile in policy_profile_names:
        if assign:
            manage_policies_tree.check_node(policy_profile)
        else:
            manage_policies_tree.uncheck_node(policy_profile)
    sel.click(manage_policies_page.save_button)


def assign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Assign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    return _assign_unassign_policy_profiles(vm_name, True, *policy_profile_names, **kwargs)


def unassign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Unassign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    return _assign_unassign_policy_profiles(vm_name, False, *policy_profile_names, **kwargs)
