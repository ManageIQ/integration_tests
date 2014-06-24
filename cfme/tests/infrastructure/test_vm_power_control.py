import cfme.web_ui.flash as flash
import pytest
import random
import time
from cfme.infrastructure.provider import RHEVMProvider
from cfme.infrastructure.virtual_machines import Vm
from utils import testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError


# GLOBAL vars
random_vm_test = []    # use the same values(provider/vm) for all the quadicon tests


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    new_idlist = []
    new_argvalues = []
    if 'random_pwr_ctl_vm' in metafunc.fixturenames:
        if random_vm_test:
            argnames, new_argvalues, new_idlist = random_vm_test
        else:
            single_index = random.choice(range(len(idlist)))
            new_idlist = ['random_provider']
            new_argvalues = argvalues[single_index]
            argnames.append('random_pwr_ctl_vm')
            new_argvalues.append('')
            new_argvalues = [new_argvalues]
            random_vm_test.append(argnames)
            random_vm_test.append(new_argvalues)
            random_vm_test.append(new_idlist)
    else:
        new_idlist = idlist
        new_argvalues = argvalues
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="class")
def vm_name():
    return "test_pwrctl_" + generate_random_string()


@pytest.fixture(scope="class")
def test_vm(request, provider_crud, provider_mgmt, vm_name):
    '''Fixture to provision appliance to the provider being tested if necessary'''
    vm = Vm(vm_name, provider_crud)

    request.addfinalizer(vm.delete_from_provider)

    if not provider_mgmt.does_vm_exist(vm_name):
        vm.create(timeout_in_minutes=15)
    return vm


@pytest.mark.usefixtures("random_pwr_ctl_vm")
class TestControlOnQuadicons(object):

    def test_power_off_cancel(self, test_vm, verify_vm_running, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_ON, timeout_in_minutes=12)
        test_vm.power_control_from_cfme(option=Vm.POWER_OFF, cancel=True)
        time.sleep(60)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-on')
        soft_assert(
            test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm not running")

    def test_power_off(self, test_vm, verify_vm_running, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_ON, timeout_in_minutes=12)
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        test_vm.power_control_from_cfme(option=Vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_OFF, timeout_in_minutes=15)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-off')
        soft_assert(
            not test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm running")

    def test_power_on_cancel(self, test_vm, verify_vm_stopped, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_OFF, timeout_in_minutes=12)
        test_vm.power_control_from_cfme(option=Vm.POWER_ON, cancel=True)
        time.sleep(60)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-off')
        soft_assert(
            not test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm running")

    def test_power_on(self, test_vm, verify_vm_stopped, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_OFF, timeout_in_minutes=12)
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        test_vm.power_control_from_cfme(option=Vm.POWER_ON, cancel=False)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_ON, timeout_in_minutes=15)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-on')
        soft_assert(
            test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm not running")


class TestVmDetailsPowerControlPerProvider(object):

    def _wait_for_last_boot_timestamp_refresh(self, vm, boot_time, timeout_in_minutes=5):
        """Timestamp update doesn't happen with state change so need a longer
        wait when expecting a last boot timestamp change"""

        def _wait_for_timestamp_refresh():
            vm.load_details(refresh=True)
            return boot_time != vm.get_detail(properties=("Power Management", "Last Boot Time"))

        try:
            wait_for(_wait_for_timestamp_refresh, num_sec=timeout_in_minutes * 60, delay=30)
        except TimedOutError:
            return False

    def _check_power_options_when_on(self, soft_assert, vm, from_details):
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=Vm.POWER_OFF, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(option=Vm.POWER_ON, from_details=from_details))
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=Vm.GUEST_SHUTDOWN, from_details=from_details))
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=Vm.SUSPEND, from_details=from_details))

        # RHEV VMs are slightly different in terms of options
        if isinstance(vm.provider_crud, RHEVMProvider):
            soft_assert(
                not vm.is_pwr_option_available_in_cfme(
                    option=Vm.GUEST_RESTART, from_details=from_details))
            soft_assert(
                not vm.is_pwr_option_available_in_cfme(option=Vm.RESET, from_details=from_details))
        else:
            soft_assert(
                vm.is_pwr_option_available_in_cfme(
                    option=Vm.GUEST_RESTART, from_details=from_details))
            soft_assert(
                vm.is_pwr_option_available_in_cfme(option=Vm.RESET, from_details=from_details))

    def _check_power_options_when_off(self, soft_assert, vm, from_details):
        soft_assert(
            vm.is_pwr_option_available_in_cfme(option=Vm.POWER_ON, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(option=Vm.POWER_OFF, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=Vm.GUEST_SHUTDOWN, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(
                option=Vm.GUEST_RESTART, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(option=Vm.SUSPEND, from_details=from_details))
        soft_assert(
            not vm.is_pwr_option_available_in_cfme(option=Vm.RESET, from_details=from_details))

    def test_power_off(self, test_vm, verify_vm_running, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(
            desired_state=Vm.STATE_ON, timeout_in_minutes=12, from_details=True)
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        self._check_power_options_when_on(soft_assert, test_vm, from_details=True)
        test_vm.power_control_from_cfme(option=Vm.POWER_OFF, cancel=False, from_details=True)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(
            desired_state='off', timeout_in_minutes=12, from_details=True)
        soft_assert(
            not test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm running")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if not isinstance(test_vm.provider_crud, RHEVMProvider):
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                "ui: " + new_last_boot_time + " should ==  orig: " + last_boot_time)

    def test_power_on(self, test_vm, verify_vm_stopped, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(
            desired_state='off', timeout_in_minutes=12, from_details=True)
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        self._check_power_options_when_off(soft_assert, test_vm, from_details=True)
        test_vm.power_control_from_cfme(option=Vm.POWER_ON, cancel=False, from_details=True)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(
            desired_state=Vm.STATE_ON, timeout_in_minutes=12, from_details=True)
        self._wait_for_last_boot_timestamp_refresh(test_vm, last_boot_time, timeout_in_minutes=10)
        soft_assert(
            test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm not running")
        new_state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        soft_assert(new_state_chg_time != state_chg_time,
            "ui: " + new_state_chg_time + " ==  orig: " + state_chg_time)
        new_last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        soft_assert(new_last_boot_time != last_boot_time,
            "ui: " + new_last_boot_time + " ==  orig: " + last_boot_time)

    def test_suspend(self, test_vm, verify_vm_running, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(
            desired_state=Vm.STATE_ON, timeout_in_minutes=12, from_details=True)
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        test_vm.power_control_from_cfme(option=Vm.SUSPEND, cancel=False, from_details=True)
        flash.assert_message_contain("Suspend initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        try:
            test_vm.wait_for_vm_state_change(
                desired_state='suspended', timeout_in_minutes=10, from_details=True)
        except TimedOutError:
            logger.warning('working around bz977489 by clicking the refresh button')
            test_vm.refresh_relationships()
            test_vm.wait_for_vm_state_change(
                desired_state=Vm.STATE_SUSPENDED, timeout_in_minutes=5, from_details=True)
        soft_assert(
            test_vm.provider_crud.get_mgmt_system().is_vm_suspended(
                test_vm.name), "vm not suspended")
        # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1101604
        if not isinstance(test_vm.provider_crud, RHEVMProvider):
            new_last_boot_time = test_vm.get_detail(
                properties=("Power Management", "Last Boot Time"))
            soft_assert(new_last_boot_time == last_boot_time,
                "ui: " + new_last_boot_time + " should ==  orig: " + last_boot_time)

    def test_start_from_suspend(self, test_vm, verify_vm_suspended, soft_assert, provider_init):
        test_vm.wait_for_vm_state_change(
            desired_state=Vm.STATE_SUSPENDED, timeout_in_minutes=12, from_details=True)
        # register_event(
        #     test_vm.provider_crud.get_yaml_data()['type'],
        #     "vm", vm_name, ["vm_power_on_req", "vm_power_on"])
        last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        self._check_power_options_when_off(soft_assert, test_vm, from_details=True)
        test_vm.power_control_from_cfme(option=Vm.POWER_ON, cancel=False, from_details=True)
        flash.assert_message_contain("Start initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(
            desired_state=Vm.STATE_ON, timeout_in_minutes=12, from_details=True)
        self._wait_for_last_boot_timestamp_refresh(test_vm, last_boot_time, timeout_in_minutes=10)
        soft_assert(
            test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm not running")
        new_state_chg_time = test_vm.get_detail(properties=("Power Management", "State Changed On"))
        soft_assert(new_state_chg_time != state_chg_time,
            "ui: " + new_state_chg_time + " should != orig: " + state_chg_time)
        new_last_boot_time = test_vm.get_detail(properties=("Power Management", "Last Boot Time"))
        soft_assert(new_last_boot_time != last_boot_time,
            "ui: " + new_last_boot_time + " should !=  orig: " + last_boot_time)


# def test_no_template_power_control(provider_crud):
#     provider_crud.load_all_provider_templates()
