# -*- coding: utf-8 -*-
import cfme.web_ui.flash as flash
import pytest
import random
import time
from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import get_all_vms
from cfme.web_ui import toolbar
from utils import testgen
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for, TimedOutError
from utils.version import appliance_is_downstream, current_version

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
def testing_vm_tools(request, provider, vm_name, full_template):
    """Fixture to provision vm with preinstalled tools to the provider being tested"""
    vm = VM.factory(vm_name, provider, template_name=full_template["name"])
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
    if provider.type == "scvmm":
        provider.refresh_provider_relationships()


def check_power_options(provider, soft_assert, vm, power_state):
    must_be_available = {'on': [vm.POWER_OFF, vm.SUSPEND, vm.RESET],
                         'off': [vm.POWER_ON]
                         }
    mustnt_be_available = {'on': [vm.POWER_ON],
                           'off': [vm.POWER_OFF, vm.SUSPEND, vm.RESET]
                           }
    # VMware and RHEVM have extended power options
    if provider.type != 'scvmm':
        must_be_available['on'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
        mustnt_be_available['off'].extend([vm.GUEST_RESTART, vm.GUEST_SHUTDOWN])
    if provider.type == 'rhevm':
        must_be_available['on'].remove(vm.RESET)
        must_be_available['on'].remove(vm.GUEST_RESTART)
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
    # check if Guest OS power operations exist and greyed from "on"
    if power_state == vm.STATE_ON and (provider.type != 'scvmm' and provider.type != 'rhevm'):
        for pwr_option in [vm.GUEST_RESTART, vm.GUEST_SHUTDOWN]:
            soft_assert(-
                toolbar.is_greyed('Power', pwr_option),
                "'{}' must be greyed/disabled in current power state - '{}' ".format(
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
        soft_assert('currentstate-on' in testing_vm.find_quadicon().state)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")

    def test_power_off(self, testing_vm, verify_vm_running, soft_assert, register_event):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=720)
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_poweroff', 'vm_poweroff'])
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=900)
        soft_assert('currentstate-off' in testing_vm.find_quadicon().state)
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
        soft_assert('currentstate-off' in testing_vm.find_quadicon().state)
        soft_assert(
            not testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm running")

    @pytest.mark.tier(1)
    def test_power_on(self, testing_vm, verify_vm_stopped, soft_assert, register_event):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_OFF, timeout=720)
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_start', 'vm_start'])
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False)
        flash.assert_message_contain("Start initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(desired_state=testing_vm.STATE_ON, timeout=900)
        soft_assert('currentstate-on' in testing_vm.find_quadicon().state)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")


class TestVmDetailsPowerControlPerProvider(object):

    def test_power_off(self, testing_vm, verify_vm_running, soft_assert, register_event):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = testing_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_poweroff', 'vm_poweroff'])
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_OFF, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Stop initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        soft_assert(
            not testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm running")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if testing_vm.provider.type != "rhevm":
            new_last_boot_time = testing_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_power_on(self, testing_vm, verify_vm_stopped, soft_assert, register_event):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_start', 'vm_start'])
        testing_vm.power_control_from_cfme(option=testing_vm.POWER_ON, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Start initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        soft_assert(
            testing_vm.provider.mgmt.is_vm_running(testing_vm.name), "vm not running")

    def test_suspend(self, testing_vm, verify_vm_running, soft_assert, register_event):
        """Tests suspend

        Metadata:
            test_flag: power_control, provision
        """
        testing_vm.wait_for_vm_state_change(
            desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = testing_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_suspend', 'vm_suspend'])
        testing_vm.power_control_from_cfme(option=testing_vm.SUSPEND, cancel=False,
                                           from_details=True)
        flash.assert_message_contain("Suspend initiated")
        if_scvmm_refresh_provider(testing_vm.provider)
        try:
            testing_vm.wait_for_vm_state_change(
                desired_state=testing_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError as e:
            if testing_vm.provider.type == "rhevm":
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise e
        soft_assert(
            testing_vm.provider.mgmt.is_vm_suspended(
                testing_vm.name), "vm not suspended")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if testing_vm.provider.type != "rhevm":
            new_last_boot_time = testing_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_start_from_suspend(
            self, testing_vm, verify_vm_suspended, soft_assert, register_event):
        """Tests start from suspend

        Metadata:
            test_flag: power_control, provision
        """
        try:
            testing_vm.provider.refresh_provider_relationships()
            testing_vm.wait_for_vm_state_change(
                desired_state=testing_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError:
            if testing_vm.provider.type == "rhevm":
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise
        register_event('VmOrTemplate', testing_vm.name, ['request_vm_start', 'vm_start'])
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
    quadicon = selected_template.find_quadicon(do_not_navigate=True, mark=True, refresh=False)
    soft_assert(not toolbar.exists("Power"), "Power displayed when template quadicon checked!")

    # Ensure there isn't a power button on the details page
    pytest.sel.click(quadicon)
    soft_assert(not toolbar.exists("Power"), "Power displayed in template details!")


@pytest.mark.uncollectif(lambda provider: provider.type == 'rhevm')
def test_power_options_from_on(provider, soft_assert, testing_vm, verify_vm_running):
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_ON, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_ON)


def test_power_options_from_off(provider, soft_assert, testing_vm, verify_vm_stopped):
    testing_vm.wait_for_vm_state_change(
        desired_state=testing_vm.STATE_OFF, timeout=720, from_details=True)
    check_power_options(provider, soft_assert, testing_vm, testing_vm.STATE_OFF)


@pytest.mark.uncollectif(lambda provider: provider.type != 'virtualcenter')
def test_guest_os_reset(testing_vm_tools, verify_vm_running, soft_assert):
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    tools_state = testing_vm_tools.get_detail(properties=("Properties", "Platform Tools"))
    soft_assert(tools_state == "toolsOk", "vmtools are not OK")
    last_boot_time = testing_vm_tools.get_detail(properties=("Power Management", "Last Boot Time"))
    testing_vm_tools.power_control_from_cfme(
        option=testing_vm_tools.GUEST_RESTART, cancel=False, from_details=True)
    flash.assert_message_contain("Restart Guest initiated")
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    wait_for_last_boot_timestamp_refresh(testing_vm_tools, last_boot_time)
    soft_assert(
        testing_vm_tools.provider.mgmt.is_vm_running(testing_vm_tools.name), "vm not running")


@pytest.mark.uncollectif(lambda provider: provider.type != 'virtualcenter')
def test_guest_os_shutdown(testing_vm_tools, verify_vm_running, soft_assert):
    testing_vm_tools.wait_for_vm_state_change(
        desired_state=testing_vm_tools.STATE_ON, timeout=720, from_details=True)
    tools_state = testing_vm_tools.get_detail(properties=("Properties", "Platform Tools"))
    soft_assert(tools_state == "toolsOk", "vmtools are not OK")
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


@pytest.mark.uncollectif(lambda: appliance_is_downstream() and current_version() < "5.4")
class TestPowerControlRESTAPI(object):
    @pytest.fixture(scope="function")
    def vm(self, rest_api, testing_vm):
        result = rest_api.collections.vms.get(name=testing_vm.name)
        assert result.name == testing_vm.name
        return result

    def test_power_off(self, vm, verify_vm_running):
        assert "stop" in vm.action
        vm.action.stop()
        wait_for(lambda: vm.power_state == "off", num_sec=300, delay=5, fail_func=vm.reload)

    def test_power_on(self, vm, verify_vm_stopped):
        assert "start" in vm.action
        vm.action.start()
        wait_for(lambda: vm.power_state == "on", num_sec=300, delay=5, fail_func=vm.reload)

    def test_suspend(self, vm, verify_vm_running):
        assert "suspend" in vm.action
        vm.action.suspend()
        wait_for(lambda: vm.power_state == "suspended", num_sec=300, delay=5, fail_func=vm.reload)


@pytest.mark.usefixtures("testing_vm")
@pytest.mark.usefixtures("setup_provider_clsscope")
@pytest.mark.uncollectif(lambda: appliance_is_downstream() and current_version() < "5.4")
class TestDeleteViaREST(object):
    # TODO: Put it somewhere else?
    @pytest.fixture(scope="function")
    def vm(self, rest_api, testing_vm):
        result = rest_api.collections.vms.get(name=testing_vm.name)
        assert result.name == testing_vm.name
        return result

    def test_delete(self, verify_vm_stopped, vm, testing_vm, rest_api):
        assert "delete" in vm.action
        vm.action.delete()
        wait_for(
            lambda: not rest_api.collections.vms.find_by(name=testing_vm.name),
            num_sec=240, delay=5)
