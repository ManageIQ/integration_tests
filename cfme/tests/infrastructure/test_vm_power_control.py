# -*- coding: utf-8 -*-
import fauxfactory
import cfme.web_ui.flash as flash
import pytest
import random
import time
from cfme.common.vm import VM
from cfme.infrastructure.virtual_machines import get_all_vms
from cfme.web_ui import toolbar
from utils import testgen
from utils.log import logger
from utils.wait import wait_for, TimedOutError
from utils.version import appliance_is_downstream, current_version

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider')]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    if not idlist:
        return
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="class")


@pytest.fixture(scope='module')
def vm_name(provider):  # Provider in order to keep the names provider-specific
    return 'test_pwrctl_' + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def test_vm(request, provider, vm_name):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = VM.factory(vm_name, provider)
    logger.info("provider_key: %s", provider.key)

    @request.addfinalizer
    def _cleanup():
        vm.delete_from_provider()
        if_scvmm_refresh_provider(provider)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm %s on provider %s", vm.name, provider.key)
    vm.provider.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


def if_scvmm_refresh_provider(provider):
    # No eventing from SCVMM so force a relationship refresh
    if provider.type == "scvmm":
        provider.refresh_provider_relationships()


class TestControlOnQuadicons(object):

    def test_power_off_cancel(self, test_vm, verify_vm_running, soft_assert):
        """Tests power off cancel

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_ON, timeout=720)
        test_vm.power_control_from_cfme(option=test_vm.POWER_OFF, cancel=True)
        if_scvmm_refresh_provider(test_vm.provider)
        # TODO: assert no event.
        time.sleep(60)
        soft_assert('currentstate-on' in test_vm.find_quadicon().state)
        soft_assert(
            test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")

    def test_power_off(self, test_vm, verify_vm_running, soft_assert, register_event):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_ON, timeout=720)
        register_event('VmOrTemplate', test_vm.name, ['request_vm_poweroff', 'vm_poweroff'])
        test_vm.power_control_from_cfme(option=test_vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=900)
        soft_assert('currentstate-off' in test_vm.find_quadicon().state)
        soft_assert(
            not test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm running")

    def test_power_on_cancel(self, test_vm, verify_vm_stopped, soft_assert):
        """Tests power on cancel

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=720)
        test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=True)
        if_scvmm_refresh_provider(test_vm.provider)
        time.sleep(60)
        soft_assert('currentstate-off' in test_vm.find_quadicon().state)
        soft_assert(
            not test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm running")

    @pytest.mark.tier(1)
    def test_power_on(self, test_vm, verify_vm_stopped, soft_assert, register_event):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=720)
        register_event('VmOrTemplate', test_vm.name, ['request_vm_start', 'vm_start'])
        test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=False)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_ON, timeout=900)
        soft_assert('currentstate-on' in test_vm.find_quadicon().state)
        soft_assert(
            test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")


class TestVmDetailsPowerControlPerProvider(object):

    def _wait_for_last_boot_timestamp_refresh(self, vm, boot_time, timeout=300):
        """Timestamp update doesn't happen with state change so need a longer
        wait when expecting a last boot timestamp change"""

        def _wait_for_timestamp_refresh():
            vm.load_details(refresh=True)
            return boot_time != vm.get_detail(properties=("Power Management", "Last Boot Time"))

        try:
            wait_for(_wait_for_timestamp_refresh, num_sec=timeout, delay=30)
        except TimedOutError:
            return False

    def _check_power_options_when_on(self, soft_assert, vm, bug, from_details):
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=vm.POWER_OFF, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=vm.POWER_ON, from_details=from_details))
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=vm.SUSPEND, from_details=from_details))

        # limited options for SCVMM providers
        if vm.provider.type != "scvmm":

            # RHEV VMs are slightly different in terms of options
            if vm.provider.type == "rhevm":
                soft_assert(
                    not vm.is_pwr_option_available_in_cfme(
                        option=vm.GUEST_RESTART, from_details=from_details))
                soft_assert(
                    not vm.is_pwr_option_available_in_cfme(
                        option=vm.RESET, from_details=from_details))
            else:
                soft_assert(
                    vm.is_pwr_option_available_in_cfme(
                        option=vm.GUEST_RESTART, from_details=from_details))
                soft_assert(
                    vm.is_pwr_option_available_in_cfme(
                        option=vm.RESET, from_details=from_details))

            vm.is_pwr_option_available_in_cfme(
                option=vm.GUEST_SHUTDOWN, from_details=from_details)
        else:
            pass

    def _check_power_options_when_off(self, soft_assert, vm, from_details):
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=vm.POWER_ON, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=vm.POWER_OFF, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=vm.GUEST_SHUTDOWN, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=vm.GUEST_RESTART, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=vm.SUSPEND, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(option=vm.RESET, from_details=from_details))

    def test_power_off(self, test_vm, verify_vm_running, soft_assert, register_event, bug):
        """Tests power off

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(
            desired_state=test_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        register_event('VmOrTemplate', test_vm.name, ['request_vm_poweroff', 'vm_poweroff'])
        self._check_power_options_when_on(soft_assert, test_vm, bug, from_details=True)
        test_vm.power_control_from_cfme(option=test_vm.POWER_OFF, cancel=False, from_details=True)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        test_vm.wait_for_vm_state_change(
            desired_state='off', timeout=720, from_details=True)
        soft_assert(
            not test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm running")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if test_vm.provider.type != "rhevm":
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_power_on(self, test_vm, verify_vm_stopped, soft_assert, register_event, bug):
        """Tests power on

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(
            desired_state='off', timeout=720, from_details=True)
        register_event('VmOrTemplate', test_vm.name, ['request_vm_start', 'vm_start'])
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        self._check_power_options_when_off(soft_assert, test_vm, from_details=True)
        test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=False, from_details=True)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        test_vm.wait_for_vm_state_change(
            desired_state=test_vm.STATE_ON, timeout=720, from_details=True)
        self._wait_for_last_boot_timestamp_refresh(test_vm, last_boot_time, timeout=600)
        soft_assert(
            test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")
        new_state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        soft_assert(new_state_chg_time != state_chg_time,
                    "ui: {} ==  orig: {}".format(new_state_chg_time, state_chg_time))
        if test_vm.provider.type != "scvmm":
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time != last_boot_time,
                        "ui: {} ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_suspend(self, test_vm, verify_vm_running, soft_assert, register_event, bug):
        """Tests suspend

        Metadata:
            test_flag: power_control, provision
        """
        test_vm.wait_for_vm_state_change(
            desired_state=test_vm.STATE_ON, timeout=720, from_details=True)
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        register_event('VmOrTemplate', test_vm.name, ['request_vm_suspend', 'vm_suspend'])
        test_vm.power_control_from_cfme(option=test_vm.SUSPEND, cancel=False, from_details=True)
        flash.assert_message_contain("Suspend initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        try:
            test_vm.wait_for_vm_state_change(
                desired_state=test_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError as e:
            if test_vm.provider.type == "rhevm":
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise e
        soft_assert(
            test_vm.provider.mgmt.is_vm_suspended(
                test_vm.name), "vm not suspended")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if test_vm.provider.type != "rhevm":
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                        "ui: {} should ==  orig: {}".format(new_last_boot_time, last_boot_time))

    def test_start_from_suspend(
            self, test_vm, verify_vm_suspended, soft_assert, register_event, bug):
        """Tests start from suspend

        Metadata:
            test_flag: power_control, provision
        """
        try:
            test_vm.provider.refresh_provider_relationships()
            test_vm.wait_for_vm_state_change(
                desired_state=test_vm.STATE_SUSPENDED, timeout=450, from_details=True)
        except TimedOutError:
            if test_vm.provider.type == "rhevm":
                logger.warning('working around bz1174858, ignoring timeout')
            else:
                raise
        register_event('VmOrTemplate', test_vm.name, ['request_vm_start', 'vm_start'])
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        self._check_power_options_when_off(soft_assert, test_vm, from_details=True)
        test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=False, from_details=True)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        if_scvmm_refresh_provider(test_vm.provider)
        test_vm.wait_for_vm_state_change(
            desired_state=test_vm.STATE_ON, timeout=720, from_details=True)
        self._wait_for_last_boot_timestamp_refresh(test_vm, last_boot_time, timeout=600)
        soft_assert(
            test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")
        new_state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        soft_assert(new_state_chg_time != state_chg_time,
                    "ui: {} should != orig: {}".format(new_state_chg_time, state_chg_time))
        if test_vm.provider.type != "scvmm":
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time != last_boot_time,
                        "ui: {} should !=  orig: {}".format(new_last_boot_time, last_boot_time))


def test_no_template_power_control(provider, setup_provider_funcscope, soft_assert):
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


@pytest.mark.uncollectif(lambda: appliance_is_downstream() and current_version() < "5.4")
class TestPowerControlRESTAPI(object):
    @pytest.fixture(scope="function")
    def vm(self, rest_api, test_vm):
        result = rest_api.collections.vms.get(name=test_vm.name)
        assert result.name == test_vm.name
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


@pytest.mark.usefixtures("test_vm")
@pytest.mark.usefixtures("setup_provider_clsscope")
@pytest.mark.uncollectif(lambda: appliance_is_downstream() and current_version() < "5.4")
class TestDeleteViaREST(object):
    # TODO: Put it somewhere else?
    @pytest.fixture(scope="function")
    def vm(self, rest_api, test_vm):
        result = rest_api.collections.vms.get(name=test_vm.name)
        assert result.name == test_vm.name
        return result

    def test_delete(self, verify_vm_stopped, vm, test_vm, rest_api):
        assert "delete" in vm.action
        vm.action.delete()
        wait_for(
            lambda: not rest_api.collections.vms.find_by(name=test_vm.name),
            num_sec=240, delay=5)
