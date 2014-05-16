"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""


import ui_navigate as nav
from cfme.exceptions import NoVmFound, NoOptionAvailable, ParmRequired, ParmConfusion
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import provider
from cfme.web_ui import Region, Quadicon, Tree, paginator, accordion, toolbar
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from utils.wait import wait_for


details_page = Region(infoblock_type='detail')

cfg_btn = partial(toolbar.select, 'Configuration')
pol_btn = partial(toolbar.select, 'Policy')
lcl_btn = partial(toolbar.select, 'Lifecycle')
mon_btn = partial(toolbar.select, 'Monitoring')
pwr_btn = partial(toolbar.select, 'Power')

visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

manage_policies_tree = Tree(
    sel.ver_pick({
        "default": "//div[@id='treebox']/div/table",
        "9.9.9.9": "//div[@id='protect_treebox']/ul"
    })
)

manage_policies_page = Region(
    locators={
        'save_button': "//div[@id='buttons_on']//img[@alt='Save Changes']",
    })


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


def on_vm_details(vm_name, force=False, provider_name=None, datacenter_name=None):
    """A function to determine if the browser is already on the proper vm details page.

    Args:
        vm_name: VM name that you are looking for.
        force: If its not on the right page, load it.
        provider_name: name of provider the vm resides on.
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
    """
    locator = "//div[@class='dhtmlxInfoBarLabel' and contains(. , 'VM and Instance') ]"
    if not sel.is_displayed(locator):
        if not force:
            return False
        else:
            load_vm_details(provider_name, datacenter_name, vm_name)
            return True

    text = sel.text(locator).encode("utf-8")
    pattern = r'("[A-Za-z0-9_\./\\-]*")'
    import re
    m = re.search(pattern, text)

    if not force:
        return vm_name == m.group().replace('"', '')
    else:
        if vm_name != m.group().replace('"', ''):
            load_vm_details(provider_name, datacenter_name, vm_name)
        else:
            return False


def load_vm_details(vm_name, provider_name=None, datacenter_name=None, refresh=False):
    """Navigates to a VM's details page.

    Args:
        vm_name: VM name that you are looking for.
        provider_name: name of provider the vm resides on.
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        refresh: Refreshes the vm page if already there

    Raises:
        TimedOutError:
            When VM does not come up to desired state in specified period of time.
        NoVmFound:
            When unable to find the VM passed
    """
    if not on_vm_details(vm_name):
        if provider_name is not None and datacenter_name is not None:
            sel.force_navigate("infra_vm_obj", context={'provider_name': provider_name,
                'datacenter_name': datacenter_name, 'vm_name': vm_name})
        elif provider_name is None:
            raise Exception("provider name and vm name are required parms")
        else:
            provider.Provider(name=provider_name).load_all_provider_vms()
            vm_quadicon = Quadicon(vm_name, 'vm')
            for page in paginator.pages():
                if sel.is_displayed(vm_quadicon):
                    sel.click(vm_quadicon)
                    break
            else:
                raise NoVmFound(vm_name)
    else:
        if refresh:
            refresh()


def does_vm_exist(vm_name, provider_name=None):
    """A function to tell you if a VM exists or not.

    Note: provider_name is optional

    Args:
        vm_name: VM name that you are looking for.
        provider_name: Name of provider the vm resides on.
    """
    if not isinstance(vm_name, str):
        raise Exception("vm_name must be a string object")
    if provider_name is not None:
        provider.Provider(name=provider_name).load_all_provider_vms()
    else:
        sel.force_navigate('infra_vm_and_templates')
    toolbar.set_vms_grid_view()
    for page in paginator.pages():
        if sel.is_displayed(Quadicon(vm_name, 'vm')):
            return True
    else:
        return False


def _determine_whether_details(vm_names, from_details=False, provider_name=None,
        datacenter_name=None):
    """A private function to handle navigating to either VM details or the VM list.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        from_details: whether to navigate to the VM details page (vm_names length must be one)
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm

    Raises:
        ParmConfusion:
            When multiple VMs passed with from_details=True
        ParmRequired:
            When no power option is passed
        NoVmFound:
            When passed VM can't be found
    """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]
    if from_details and len(vm_names) == 1 and provider_name is not None:
        load_vm_details(vm_names[0], provider_name, datacenter_name)
    elif from_details and provider_name is None:
        raise ParmRequired("from_details flag requires provider_name")
    elif from_details and len(vm_names) > 1:
        raise ParmConfusion("Only one VM can be passed with from_details flag")
    elif len(vm_names) < 1:
        raise ParmRequired("At least one VM must be passed")
    else:
        sel.force_navigate('infra_vm_and_templates')
        if len(vm_names) == 1 and sel.is_displayed(Quadicon(vm_names[0], 'vm')):
            return
        if provider_name is not None:
            provider.Provider(name=provider_name).load_all_provider_vms()
        if len(vm_names) > 1:
            paginator.results_per_page(1000)
        else:
            if not does_vm_exist(vm_names[0]):
                raise NoVmFound("vm named " + vm_names[0] + " not found")


def remove(vm_names, cancel=True, from_details=False, provider_name=None, datacenter_name=None):
    """Removes a VM from CFME VMDB

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        cancel: Whether to cancel the deletion, defaults to True
        from_details: whether to delete from the details page (vm_names length must be one)
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
    """

    _determine_whether_details(vm_names, from_details=from_details,
        provider_name=provider_name, datacenter_name=datacenter_name)
    if from_details:
        cfg_btn('Remove from the VMDB', invokes_alert=True)
    else:
        for vm_name in vm_names:
            sel.click(Quadicon(vm_name, 'vm').checkbox())
        cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def get_detail(vm_name, provider_name=None, datacenter_name=None, properties=None):
    """Gets details from the details infoblock

    The function first ensures that we are on the detail page for the specific vm.

    Args:
        vm_name: name of vm_name
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

    Returns:
        A string representing the contents of the InfoBlock's value.
    """
    on_vm_details(vm_name, provider_name=provider_name, datacenter_name=datacenter_name, force=True)
    return details_page.infoblock.text(*properties)


def wait_for_vm_state_change(vm_name, desired_state, timeout_in_minutes, provider_name=None,
        datacenter_name=None, from_details=False):
    """Wait for VM to come to desired state.

    This function waits just the needed amount of time thanks to wait_for.

    Args:
        vm_name: Displayed name of the VM
        desired_state: 'on' or 'off'
        timeout_in_minutes: Specify amount of time to wait until TimedOutError is raised in minutes.
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        from_details: Whether or not to check state from vm details page (vm_names length must
            be one) or from the vms list

    Raises:
        TimedOutError:
            When VM does not come up to desired state in specified period of time.
        NoVmFound:
            When unable to find the VM passed
    """
    def _check():
        toolbar.refresh()
        if from_details:
            detail_t = "Power Management", "Power State"
            return get_detail(vm_name, provider_name=provider_name,
                datacenter_name=datacenter_name, properties=detail_t) == desired_state
        else:
            if does_vm_exist(vm_name):
                return Quadicon(vm_name, 'vm').state == 'currentstate-' + desired_state
            else:
                raise NoVmFound("vm named " + vm_name + " not found")

    _determine_whether_details([vm_name], provider_name=provider_name,
        datacenter_name=datacenter_name, from_details=from_details)
    return wait_for(_check, num_sec=timeout_in_minutes * 60)


def _is_pwr_helper(vm_names, from_details=False, provider_name=None, datacenter_name=None,
        option=None):
    """A private function to get setup for the other power control functions.

    This function gets navigates to the correct page and if not details, marks checkboxes.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree when
            navigating to the vm
        option: Power option param.
    """
    _determine_whether_details(vm_names, from_details=from_details, provider_name=provider_name,
        datacenter_name=datacenter_name)
    if not from_details:
        for vm_name in vm_names:
            sel.click(Quadicon(vm_name, 'vm').checkbox())
    if option is None:
        raise ParmRequired("power option parm is required")


def is_pwr_option_visible(vm_names, from_details=False, provider_name=None, datacenter_name=None,
        option=None):
    """Returns whether a particular power option is visible.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed, only one VM can
            be passed in the list.
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        option: Power option param.

    Raises:
        ParmRequired:
            When no power option is passed
    """
    _is_pwr_helper(vm_names, from_details=from_details, provider_name=provider_name,
        datacenter_name=datacenter_name, option=option)
    try:
        toolbar.is_greyed('Power', option)
        return True
    except NoSuchElementException:
        return False


def is_pwr_option_enabled(vm_names, from_details=False, provider_name=None, datacenter_name=None,
        option=None):
    """Returns whether a particular power option is enabled.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        from_details: Whether or not to perform action from vm details page (vm_names length must
            be one) or from the vms list
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        option: Power option param.

    Raises:
        NoOptionAvailable:
            When unable to find the power option passed
        ParmRequired:
            When no power option is passed
    """
    _is_pwr_helper(vm_names, from_details=from_details, provider_name=provider_name,
        datacenter_name=datacenter_name, option=option)
    try:
        return not toolbar.is_greyed('Power', option)
    except NoSuchElementException:
        raise NoOptionAvailable("No such power option (" + str(option) + ") is available")


def do_power_control(vm_names, from_details=False, provider_name=None, datacenter_name=None,
        option=None, cancel=True):
    """Executes a power option against a list of VMs.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree when
            navigating to the vm
        from_details: Whether or not to perform action from vm details page (vm_names length
            must be one) or from the vms list
        cancel: Whether or not to cancel the power control action
        option: Power option param.

    Raises:
        NoOptionAvailable:
            When unable to find the power option passed
        ParmRequired:
            When no power option is passed
    """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]

    _is_pwr_helper(vm_names, from_details=from_details, provider_name=provider_name,
        datacenter_name=datacenter_name, option=option)

    if is_pwr_option_visible(vm_names, from_details=from_details, provider_name=provider_name,
            datacenter_name=datacenter_name, option=option) and \
            is_pwr_option_enabled(vm_names, from_details=from_details,
                provider_name=provider_name, datacenter_name=datacenter_name, option=option):

                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)


def refresh_relationships(vm_names, from_details=False, provider_name=None, datacenter_name=None,
        cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed,
            only one VM can be passed in the list.
        provider_name: name of provider vm resides on, only needed if fromDetails=True
        datacenter_name: When passed with provider_name, allows navigation through tree
            when navigating to the vm
        from_details: Whether or not to perform action from vm details page (vm_names length must
            be one) or from the vms list
        cancel: Whether or not to cancel the refresh relationships action
    """
    _determine_whether_details(vm_names, from_details=from_details, provider_name=provider_name,
        datacenter_name=datacenter_name)
    cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def get_all_vms(do_not_navigate=False):
    """Returns list of all hosts"""
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    vms = set([])
    try:
        for page in paginator.pages():
            for title in sel.elements(
                    "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')]"):
                vms.add(sel.get_attribute(title, "title"))
        return vms
    except NoSuchElementException:
        return set([])


def find_quadicon(vm, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific vm

    Args:
        vm: Host name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    for page in paginator.pages():
        quadicon = Quadicon(vm, "vm")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
        raise NoVmFound("VM '{}' not found in UI!".format(vm))


def _assign_unassign_policy_profiles(vm_name, assign, *policy_profile_names, **kwargs):
    """DRY function for managing policy profiles.

    See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

    Args:
        vm_name: Name of the VM.
        assign: Wheter to assign or unassign.
        policy_profile_names: :py:class:`str` with Policy Profile names.

    Keywords:
        datastore_name, provider_name: see :py:func:`load_vm_details`
    """
    load_vm_details(vm_name, **kwargs)
    toolbar.select("Policy", "Manage Policies")
    for policy_profile in policy_profile_names:
        if assign:
            manage_policies_tree.select_node(policy_profile)
        else:
            manage_policies_tree.deselect_node(policy_profile)
    sel.click(manage_policies_page.save_button)


def assign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Assign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.

    Keywords:
        datastore_name, provider_name: see :py:func:`load_vm_details`
    """
    return _assign_unassign_policy_profiles(vm_name, True, *policy_profile_names, **kwargs)


def unassign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Unassign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.

    Keywords:
        datastore_name, provider_name: see :py:func:`load_vm_details`
    """
    return _assign_unassign_policy_profiles(vm_name, False, *policy_profile_names, **kwargs)
