# -*- coding: utf-8 -*-
import cfme.web_ui.flash as flash
import pytest
import random
import time
from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.virtual_machines import get_all_vms
from cfme.web_ui import toolbar
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.power]


pytest_generate_tests = testgen.generate([InfraProvider], scope="class")


@pytest.fixture(scope='function')
def vm_name():
    return random_vm_name('pwr-c')


@pytest.fixture(scope="function")
def testing_vm(request, provider, vm_name):
    """Fixture to provision vm to the provider being tested"""
    vm = VM.factory(vm_name, provider)
    logger.info("provider_key: %s", provider.key)

    @request.addfinalizer
    def _cleanup():
        vm.delete_from_provider()
        if_scvmm_refresh_provider(provider)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    return vm


@pytest.fixture(scope="function")
def archived_vm(provider, testing_vm):
    """Fixture to archive testing VM"""
    provider.mgmt.delete_vm(testing_vm.name)
    testing_vm.wait_for_vm_state_change(desired_state='archived', timeout=720,
                                        from_details=False, from_any_provider=True)


@pytest.fixture(scope="function")
def orphaned_vm(provider, testing_vm):
    """Fixture to orphane VM by removing provider from CFME"""
    provider.delete_if_exists(cancel=False)
    testing_vm.wait_for_vm_state_change(desired_state='orphaned', timeout=720,
                                        from_details=False, from_any_provider=True)


@pytest.fixture(scope="function")
def testing_vm_tools(request, provider, vm_name, full_template):
    """Fixture to provision vm with preinstalled tools to the provider being tested"""
    vm = VM.factory(vm_name, provider, template_name=full_template.name)
    logger.info("provider_key: %s", provider.key)

    @request.addfinalizer
    def _cleanup():
        vm.delete_from_provider()
        if_scvmm_refresh_provider(provider)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    return vm


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
        mustnt_be_available['on'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
        mustnt_be_available['off'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
    if provider.one_of(RHEVMProvider):
        must_be_available['on'].remove(vm.RESET)
    vm.load_details()
    toolbar.pf_select('Power')
    for pwr_option in must_be_available[power_state]:
        soft_assert(
            toolbar.exists('Power', pwr_option),
            "'{}' must be available in current power state - '{}' ".format(
                pwr_option, power_state))
    for pwr_option in mustnt_be_available[power_state]:
        soft_assert(
            not toolbar.exists('Power', pwr_option),
            "'{}' must not be available in current power state - '{}' ".format(
                pwr_option, power_state))


def wait_for_last_boot_timestamp_refresh(vm, boot_time, timeout=300):
    """Timestamp update doesn't happen with state change so need a longer
    wait when expecting a last boot timestamp change"""

    def _wait_for_timestamp_refresh():
        vm.load_details(refresh=True)
        return boot_time != vm.get_detail(properties=("Power Management", "Last Boot Time"))

    try:
        wait_for(_wait_for_timestamp_refresh, num_sec=timeout, delay=30)
    except TimedOutError:
        return False


def wait_for_vm_tools(vm, timeout=300):
    """Sometimes test opens VM details before it gets loaded and can't verify if vmtools are
    installed"""

    def _wait_for_tools_ok():
        vm.load_details(refresh=True)
        return vm.get_detail(properties=("Properties", "Platform Tools")) == 'toolsOk'
    try:
        wait_for(_wait_for_tools_ok, num_sec=timeout, delay=10)
    except TimedOutError:
        return False


class TestControlOnQuadicons(object):

    def test_power_off_cancel(self, testing_vm, verify_vm_running, soft_assert):
        """Tests power off cancel

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=True)
        if_scvmm_refresh_provider(testing_vm.provider)
        # TODO: assert no event.
        time.sleep(60)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert('currentstate-on' in vm_state)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")

    def test_power_off(self, testing_vm, verify_vm_running, soft_assert):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=900)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert('currentstate-off' in vm_state)
        soft_assert(
            not testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm running")

    def test_power_on_cancel(self, testing_vm, verify_vm_stopped, soft_assert):
        """Tests power on cancel

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=True)
        if_scvmm_refresh_provider(testing_vm.provider)
        time.sleep(60)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert('currentstate-off' in vm_state)
        soft_assert(
            not testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm running")

    @pytest.mark.tier(1)
    def test_power_on(self, testing_vm, verify_vm_stopped, soft_assert):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=720)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False)
        flash.assert_message_contain("Start initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=900)
        vm_state = testing_vm.find_quadicon().data['state']
        soft_assert('currentstate-on' in vm_state)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")


class TestVmDetailsPowerControlPerProvider(object):

    def test_power_off(self, testing_vm, verify_vm_running, soft_assert):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = testing_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Stop initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        soft_assert(
            not testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm running")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if not testing_vm.provider.one_of(RHEVMProvider):
            new_last_boot_time = testing_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_power_on(self, testing_vm, verify_vm_stopped, soft_assert):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Start initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")

    def test_suspend(self, testing_vm, verify_vm_running, soft_assert):
        """Tests suspend

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = testing_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        testing_vm.power_control_from_cfme(option=testing_vm.SUSPEND, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Suspend initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        try:
            testing_vm.wait_for_vm_state_change(
                desired_state=testing_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError as e:
            if testing_vm.provider.one_of(RHEVMProvider):
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise e
        soft_assert(
            testing_vm.provider.mgmt.is_vm_suspended(
                testing_vm.name), "vm not suspended")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if not testing_vm.provider.one_of(RHEVMProvider):
            new_last_boot_time = testing_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_start_from_suspend(
            self, testing_vm, verify_vm_suspended, soft_assert):
        """Tests start from suspend

        Metadata:
            test_flag: power_control, provision
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
        last_boot_time = testing_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Start initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        wait_for_last_boot_timestamp_refresh(testing_vm, last_boot_time, timeout=600)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")


@pytest.mark.meta(blockers=[BZ(1496383, forced_streams=['5.7', '5.8', '5.9', 'upstream'])])
def test_no_template_power_control(provider, soft_assert):
    """ Ensures that no power button is displayed for templates.

    Prerequisities:
        * An infra provider that has some templates.

    Steps:
        * Open the view of all templates of the provider
        * Verify the Power toolbar button is not visible
        * Select some template using the checkbox
        * Verify the Power toolbar button is not visible
        * Click on some template to get into the details page
        * Verify the Power toolbar button is not visible
    """
    provider.load_all_provider_templates()
    toolbar.select('Grid View')
    soft_assert(not toolbar.exists("Power"), "Power displayed in template grid view!")

    # Ensure selecting a template doesn't cause power menu to appear
    templates = list(get_all_vms(True))
    template_name = random.choice(templates)
    selected_template = VM.factory(template_name, provider, template=True)

    # Check the power button with checking the quadicon
    entity = selected_template.find_quadicon()
    entity.check()
    soft_assert(not toolbar.exists("Power"), "Power displayed when template quadicon checked!")

    # Ensure there isn't a power button on the details page
    entity.click()
    soft_assert(not toolbar.exists("Power"), "Power displayed in template details!")


def test_no_power_controls_on_archived_vm(testing_vm, archived_vm, soft_assert):
    """ Ensures that no power button is displayed from details view of archived vm

    Prerequisities:
        * Archived VM
    Steps:
        * Open the view of VM Details
        * Verify the Power toolbar button is not visible
    """
    testing_vm.load_details(from_any_provider=True)
    soft_assert(not toolbar.exists("Power"), "Power displayed in template details!")


def test_archived_vm_status(testing_vm, archived_vm):
    vm_state = testing_vm.find_quadicon(from_any_provider=True).data['state']
    assert ('currentstate-archived' in vm_state)


def test_orphaned_vm_status(testing_vm, orphaned_vm):
    vm_state = testing_vm.find_quadicon(from_any_provider=True).data['state']
    assert ('currentstate-orphaned' in vm_state)


@pytest.mark.uncollectif(lambda provider: provider.one_of(RHEVMProvider))
def test_power_options_from_on(provider, soft_assert, testing_vm, verify_vm_running):
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_ON)


def test_power_options_from_off(provider, soft_assert, testing_vm, verify_vm_stopped):
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_OFF)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_guest_os_reset(testing_vm_tools, verify_vm_running, soft_assert):
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    wait_for_vm_tools(testing_vm_tools)
    last_boot_time = testing_vm_tools.get_detail(properties=("Power Management", "Last Boot Time"))
    testing_vm_tools.power_control_from_cfme(
        option=testing_vm_tools.GUEST_RESTART, cancel=False, from_details=True)
    flash.assert_message_contain("Restart Guest initiated")
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    wait_for_last_boot_timestamp_refresh(testing_vm_tools, last_boot_time)
    soft_assert(
        testing_vm_tools.provider.mgmt.is_vm_running(testing_vm_tools.name), "vm not running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_guest_os_shutdown(testing_vm_tools, verify_vm_running, soft_assert):
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    wait_for_vm_tools(testing_vm_tools)
    last_boot_time = testing_vm_tools.get_detail(properties=("Power Management", "Last Boot Time"))
    testing_vm_tools.power_control_from_cfme(
        option=testing_vm_tools.GUEST_SHUTDOWN, cancel=False, from_details=True)
    flash.assert_message_contain("Shutdown Guest initiated")
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_OFF, timeout=720, from_details=True)
    soft_assert(
        not testing_vm_tools.provider.mgmt.is_vm_running(testing_vm_tools.name), "vm running")
    new_last_boot_time = testing_vm_tools.get_detail(
        properties=("Power Management", "Last Boot Time"))
    soft_assert(new_last_boot_time == last_boot_time,
                "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))
