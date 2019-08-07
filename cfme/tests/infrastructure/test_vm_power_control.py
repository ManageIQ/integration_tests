# -*- coding: utf-8 -*-
import random
import time

import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.base.login import BaseLoggedInPage
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.rest.gen_data import users as _users
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.power,
    pytest.mark.provider([InfraProvider], scope='class'),
]


@pytest.fixture(scope='function')
def vm_name():
    return random_vm_name('pwr-c')


@pytest.fixture(scope="function")
def testing_vm(appliance, request, provider, vm_name):
    """Fixture to provision vm to the provider being tested"""
    vm = appliance.collections.infra_vms.instantiate(vm_name, provider)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    yield vm
    vm.cleanup_on_provider()
    if_scvmm_refresh_provider(provider)


@pytest.fixture(scope="function")
def archived_vm(provider, testing_vm):
    """Fixture to archive testing VM"""
    testing_vm.mgmt.delete()
    testing_vm.wait_for_vm_state_change(desired_state='archived', timeout=720,
                                        from_details=False, from_any_provider=True)


@pytest.fixture(scope="function")
def orphaned_vm(provider, testing_vm):
    """Fixture to orphane VM by removing provider from CFME"""
    provider.delete_if_exists(cancel=False)
    testing_vm.wait_for_vm_state_change(desired_state='orphaned', timeout=720,
                                        from_details=False, from_any_provider=True)


@pytest.fixture(scope="function")
def testing_vm_tools(appliance, request, provider, vm_name, full_template):
    """Fixture to provision vm with preinstalled tools to the provider being tested"""
    vm = appliance.collections.infra_vms.instantiate(vm_name, provider, full_template.name)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    yield vm
    vm.cleanup_on_provider()
    if_scvmm_refresh_provider(provider)


def if_scvmm_refresh_provider(provider):
    # No eventing from SCVMM so force a relationship refresh
    if provider.one_of(SCVMMProvider):
        provider.refresh_provider_relationships()


def check_power_options(provider, soft_assert, vm, power_state):
    must_be_available = {
        'on': [vm.POWER_OFF, vm.SUSPEND, vm.RESET],
        'off': [vm.POWER_ON]
    }
    mustnt_be_available = {
        'on': [vm.POWER_ON],
        'off': [vm.POWER_OFF, vm.SUSPEND, vm.RESET]
    }
    # VMware and RHEVM have extended power options
    if not provider.one_of(SCVMMProvider):
        mustnt_be_available['off'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
    if not provider.one_of(SCVMMProvider, RHEVMProvider):
        mustnt_be_available['on'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
    if provider.one_of(RHEVMProvider):
        must_be_available['on'].remove(vm.RESET)

    view = navigate_to(vm, 'Details')
    power_dropdown = view.toolbar.power
    for pwr_option in must_be_available[power_state]:
        soft_assert(power_dropdown.item_enabled(pwr_option),
                    "'{}' must be available in current power state - '{}' ".format(pwr_option,
                                                                                   power_state))
    for pwr_option in mustnt_be_available[power_state]:
        pwr_state = power_dropdown.has_item(pwr_option) and power_dropdown.item_enabled(pwr_option)
        soft_assert(not pwr_state,
                    "'{}' must not be available in current power state - '{}' ".format(pwr_option,
                                                                                       power_state))


def wait_for_last_boot_timestamp_refresh(vm, boot_time, timeout=300):
    """Timestamp update doesn't happen with state change so need a longer
    wait when expecting a last boot timestamp change"""
    view = navigate_to(vm, "Details")

    def _wait_for_timestamp_refresh():
        cur_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
        return boot_time != cur_boot_time

    try:
        wait_for(_wait_for_timestamp_refresh, num_sec=timeout, delay=30,
                 fail_func=view.toolbar.reload.click)
        return True
    except TimedOutError:
        return False


def ensure_state_changed_on_unchanged(vm, state_changed_on):
    """Returns True if current value of State Changed On in the Power Management
    is the same as the supplied (original) value."""
    view = navigate_to(vm, "Details")
    new_state_changed_on = view.entities.summary("Power Management").get_text_of("State Changed On")
    return state_changed_on == new_state_changed_on


def wait_for_vm_tools(vm, timeout=300):
    """Sometimes test opens VM details before it gets loaded and can't verify if vmtools are
    installed"""
    view = navigate_to(vm, "Details")

    def _wait_for_tools_ok():
        return view.entities.summary("Properties").get_text_of("Platform Tools") == 'toolsOk'

    try:
        wait_for(_wait_for_tools_ok, num_sec=timeout, delay=10, fail_func=view.toolbar.reload.click)
    except TimedOutError:
        return False


class TestControlOnQuadicons(object):

    @pytest.mark.rhv3
    def test_power_off_cancel(self, testing_vm, ensure_vm_running, soft_assert):
        """Tests power off cancel

        Metadata:
            test_flag: power_control, provision

        Polarion:
            assignee: ghubale
            casecomponent: Infra
            initialEstimate: 1/10h
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=True)
        if_scvmm_refresh_provider(testing_vm.provider)
        # TODO: assert no event.
        time.sleep(60)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert(vm_state == 'on')
        soft_assert(
            testing_vm.mgmt.is_running, "vm not running")

    @pytest.mark.rhv1
    def test_power_off(self, appliance, testing_vm, ensure_vm_running, soft_assert):
        """Tests power off

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False)

        view = appliance.browser.create_view(BaseLoggedInPage)
        view.flash.assert_success_message(text='Stop initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=900)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert(vm_state == 'off')
        soft_assert(not testing_vm.mgmt.is_running, "vm running")

    @pytest.mark.rhv3
    def test_power_on_cancel(self, testing_vm, ensure_vm_stopped, soft_assert):
        """Tests power on cancel

        Polarion:
            assignee: ghubale
            initialEstimate: 1/4h
            casecomponent: Infra
            caseimportance: high
            tags: power
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=True)
        if_scvmm_refresh_provider(testing_vm.provider)
        time.sleep(60)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert(vm_state == 'off')
        soft_assert(not testing_vm.mgmt.is_running, "vm running")

    @pytest.mark.rhv1
    @pytest.mark.tier(1)
    def test_power_on(self, appliance, testing_vm, ensure_vm_stopped, soft_assert):
        """Tests power on

        Metadata:
            test_flag: power_control, provision

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False)

        view = appliance.browser.create_view(BaseLoggedInPage)
        view.flash.assert_success_message(text='Start initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=900)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert(vm_state == 'on')
        soft_assert(testing_vm.mgmt.is_running, "vm not running")


class TestVmDetailsPowerControlPerProvider(object):

    @pytest.mark.rhv3
    def test_power_off(self, appliance, testing_vm, ensure_vm_running, soft_assert):
        """Tests power off

        Metadata:
            test_flag: power_control, provision

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        view = navigate_to(testing_vm, "Details")
        last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False,
                                           from_details=True)

        view.flash.assert_success_message(text='Stop initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        soft_assert(not testing_vm.mgmt.is_running, "vm running")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if not testing_vm.provider.one_of(RHEVMProvider):
            new_last_boot_time = view.entities.summary("Power Management").get_text_of(
                "Last Boot Time")
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    @pytest.mark.rhv3
    def test_power_on(self, appliance, testing_vm, ensure_vm_stopped, soft_assert):
        """Tests power on

        Metadata:
            test_flag: power_control, provision

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False,
                                           from_details=True)

        view = appliance.browser.create_view(BaseLoggedInPage)
        view.flash.assert_success_message(text='Start initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        soft_assert(testing_vm.mgmt.is_running, "vm not running")

    @pytest.mark.rhv3
    @pytest.mark.meta(automates=[BZ(1174858)])
    def test_suspend(self, appliance, testing_vm, ensure_vm_running, soft_assert):
        """Tests suspend

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power

        Bugzilla:
            1174858
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        view = navigate_to(testing_vm, "Details")
        last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
        testing_vm.power_control_from_cfme(option=testing_vm.SUSPEND,
                                           cancel=False,
                                           from_details=True)

        view.flash.assert_success_message(text='Suspend initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_SUSPENDED,
                                            timeout=450,
                                            from_details=True)
        soft_assert(testing_vm.mgmt.is_suspended, "vm not suspended")
        if not testing_vm.provider.one_of(RHEVMProvider):
            new_last_boot_time = view.entities.summary("Power Management").get_text_of(
                "Last Boot Time")
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    @pytest.mark.rhv1
    def test_start_from_suspend(self, appliance, testing_vm, ensure_vm_suspended, soft_assert):
        """Tests start from suspend

        Polarion:
            assignee: ghubale
            initialEstimate: 1/6h
            casecomponent: Infra
            caseimportance: high
            tags: power

        """
        try:
            testing_vm.provider.refresh_provider_relationships()
            testing_vm.wait_for_vm_state_change(
                desired_state=testing_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError:
            if testing_vm.provider.one_of(RHEVMProvider):
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise
        view = navigate_to(testing_vm, "Details")
        last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False,
                                           from_details=True)

        view.flash.assert_success_message(text='Start initiated', partial=True)

        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        wait_for_last_boot_timestamp_refresh(testing_vm, last_boot_time, timeout=600)
        soft_assert(testing_vm.mgmt.is_running, "vm not running")


@pytest.mark.rhv3
def test_no_template_power_control(provider, soft_assert):
    """ Ensures that no power button is displayed for templates.

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        initialEstimate: 1/10h
        setup:
            1. An infra provider that has some templates.
        testSteps:
            1. Open the view of all templates of the provider
            2. Verify the Power toolbar button is not visible
            3. Select some template using the checkbox
            4. Verify the Power toolbar button is not visible
            5. Click on some template to get into the details page
            6. Verify the Power toolbar button is not visible

    Bugzilla:
        1496383
        1634713
    """
    view = navigate_to(provider, 'ProviderTemplates')
    view.toolbar.view_selector.select('Grid View')
    soft_assert(not view.toolbar.power.is_displayed, "Power displayed in template grid view!")

    # Ensure selecting a template doesn't cause power menu to appear
    templates = view.entities.all_entity_names
    template_name = random.choice(templates)
    selected_template = provider.appliance.collections.infra_templates.instantiate(template_name,
                                                                                   provider)

    # Check the power button with checking the quadicon
    view = navigate_to(selected_template, 'AllForProvider', use_resetter=False)
    entity = view.entities.get_entity(name=selected_template.name, surf_pages=True)
    entity.check()
    for action in view.toolbar.power.items:
        # Performing power actions on template
        view.toolbar.power.item_select(action, handle_alert=True)
        if action == 'Power On':
            action = 'Start'
        elif action == 'Power Off':
            action = 'Stop'
        view.flash.assert_message('{} action does not apply to selected items'.format(action))
        view.flash.dismiss()

    # Ensure there isn't a power button on the details page
    entity.click()
    soft_assert(not view.toolbar.power.is_displayed, "Power displayed in template details!")


@pytest.mark.rhv3
@pytest.mark.meta(
    blockers=[
        BZ(
            1723805,
            unblock=lambda provider: not provider.one_of(SCVMMProvider),
        )
    ]
)
def test_no_power_controls_on_archived_vm(appliance, testing_vm, archived_vm, soft_assert):
    """ Ensures that no power button is displayed from details view of archived vm

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        initialEstimate: 1/10h
        setup:
            1. Archived VM should be available
        testSteps:
            1. Open the view of VM Details
            2. Verify the Power toolbar button is not visible

    Bugzilla:
        1520489
        1659340
    """
    view = navigate_to(testing_vm, 'AnyProviderDetails', use_resetter=False)
    status = getattr(view.toolbar.power, "is_enabled")
    assert not status, "Power displayed in archived VM's details!"


@pytest.mark.rhv3
def test_archived_vm_status(testing_vm, archived_vm):
    """Tests archived vm status

    Metadata:
        test_flag: inventory

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: power
    """
    vm_state = testing_vm.find_quadicon(from_any_provider=True).data['state']
    assert (vm_state == 'archived')


@pytest.mark.rhv3
def test_orphaned_vm_status(testing_vm, orphaned_vm):
    """Tests orphaned vm status

    Polarion:
        assignee: ghubale
        initialEstimate: 1/10h
        casecomponent: Infra
        tags: power
    """
    vm_state = testing_vm.find_quadicon(from_any_provider=True).data['state']
    assert (vm_state == 'orphaned')


@pytest.mark.rhv1
def test_vm_power_options_from_on(provider, soft_assert, testing_vm, ensure_vm_running):
    """Tests vm power options from on

    Metadata:
        test_flag: power_control

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_ON)


@pytest.mark.rhv3
@pytest.mark.meta(automates=[BZ(1724062)])
def test_vm_power_options_from_off(provider, soft_assert, testing_vm, ensure_vm_stopped):
    """Tests vm power options from off

    Metadata:
        test_flag: power_control

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        initialEstimate: 1/4h

    Bugzilla:
        1724062
    """
    # TODO(ghubale@redhat.com): Update this test case with power options(shutdown and restart guest)
    #  for scvmm provider
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_OFF)


@pytest.mark.provider([VMwareProvider, RHEVMProvider], override=True, scope='function')
@pytest.mark.meta(automates=[1571830, 1650506])
def test_guest_os_reset(appliance, provider, testing_vm_tools, ensure_vm_running, soft_assert):
    """Tests vm guest os reset

    Metadata:
        test_flag: power_control

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        casecomponent: Infra
        tags: power

    Bugzilla:
        1571830
        1650506
    """
    # TODO(ghubale@redhat.com): Update this test case for power operation(restart guest) for scvmm
    wait_for_vm_tools(testing_vm_tools)
    view = navigate_to(testing_vm_tools, "Details")
    last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
    state_changed_on = view.entities.summary("Power Management").get_text_of("State Changed On")
    testing_vm_tools.power_control_from_cfme(
        option=testing_vm_tools.GUEST_RESTART, cancel=False, from_details=True)
    view.flash.assert_success_message(text='Restart Guest initiated', partial=True)
    if not (provider.one_of(RHEVMProvider) and BZ(1571830, forced_streams=["5.10", "5.11"]).blocks):
        soft_assert(
            wait_for_last_boot_timestamp_refresh(testing_vm_tools, last_boot_time),
            "Last Boot Time value has not been refreshed",
        )
    soft_assert(
        ensure_state_changed_on_unchanged(testing_vm_tools, state_changed_on),
        "Value of 'State Changed On' has changed after guest restart",
    )
    soft_assert(testing_vm_tools.mgmt.is_running, "vm not running")


@pytest.mark.meta(automates=[1723485, 1571895, 1650506])
@pytest.mark.provider([VMwareProvider, RHEVMProvider], override=True)
@pytest.mark.meta(blockers=[BZ(1723485, forced_streams=["5.11"],
                               unblock=lambda provider: not (provider.one_of(RHEVMProvider)
                                                             and not provider.version < 4.3))])
def test_guest_os_shutdown(appliance, provider, testing_vm_tools, ensure_vm_running, soft_assert):
    """Tests vm guest os reset

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: high
        casecomponent: Infra
        tags: power

    Bugzilla:
        1723485
        1571895
        1650506
    """
    # TODO(ghubale@redhat.com): Update this test case for power operation(shutdown guest) for scvmm
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    wait_for_vm_tools(testing_vm_tools)
    view = navigate_to(testing_vm_tools, "Details")
    last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
    testing_vm_tools.power_control_from_cfme(
        option=testing_vm_tools.GUEST_SHUTDOWN, cancel=False, from_details=True)

    view.flash.assert_success_message(text='Shutdown Guest initiated', partial=True)

    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_OFF, timeout=720, from_details=True)
    soft_assert(
        not testing_vm_tools.mgmt.is_running, "vm running")

    # Blocking this assertion for RHEV providers because of BZ(1571895) not fixed yet
    if not (BZ(1571895, forced_streams=["5.10", "5.11"]).blocks and provider.one_of(RHEVMProvider)):
        new_last_boot_time = view.entities.summary("Power Management").get_text_of("Last Boot Time")
        soft_assert(new_last_boot_time == last_boot_time,
                    "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))


@pytest.fixture(scope="function")
def new_user(request, appliance):
    user, user_data = _users(request, appliance, group="EvmGroup-vm_user")
    yield appliance.collections.users.instantiate(
        name=user[0].name,
        credential=Credential(principal=user_data[0]["userid"], secret=user_data[0]["password"]),
    )

    if user[0].exists:
        user[0].action.delete()


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1687597])
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, override=True)
def test_retire_vm_with_vm_user_role(new_user, appliance, testing_vm):
    """
    Bugzilla:
        1687597

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.10
        casecomponent: Automate
        setup:
            1. Provision vm
        testSteps:
            1. Create custom user with 'EvmRole_vm-user' role
            2. Retire VM by log-in to custom user
    """
    # Log in with new user to retire the vm
    with new_user:
        view = navigate_to(testing_vm.parent, "All")
        view.entities.get_entity(name=testing_vm.name, surf_pages=True).check()
        assert view.toolbar.lifecycle.item_enabled("Retire selected items")
        testing_vm.retire()
        assert testing_vm.wait_for_vm_state_change(desired_state="retired", timeout=720,
                                                   from_details=True)
