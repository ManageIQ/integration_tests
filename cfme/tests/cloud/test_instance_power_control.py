# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.web_ui.flash as flash
from cfme import test_requirements
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError, RefreshTimer


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.long_running,
    test_requirements.power,
    pytest.mark.provider([CloudProvider], scope='function', required_fields=['test_power_control'])
]


@pytest.yield_fixture(scope="function")
def testing_instance(setup_provider, provider):
    """ Fixture to provision instance on the provider
    """
    instance = Instance.factory(random_vm_name('pwr-c'), provider)
    if not provider.mgmt.does_vm_exist(instance.name):
        instance.create_on_provider(allow_skip="default")
    elif instance.provider.type == "ec2" and \
            provider.mgmt.is_vm_state(instance.name, provider.mgmt.states['deleted']):
        provider.mgmt.set_name(
            instance.name, 'test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    provider.refresh_provider_relationships()

    # Make sure the instance shows up
    try:
        wait_for(lambda: instance.exists,
                 fail_condition=False,
                 num_sec=600,
                 delay=15,
                 fail_func=provider.refresh_provider_relationships)
    except TimedOutError:
        pytest.fail('Failed to find instance in CFME after creating on provider: {}'
                    .format(instance.name))

    yield instance

    logger.info('Fixture cleanup, deleting test instance: %s', instance.name)
    try:
        provider.mgmt.delete_vm(instance.name)
    except Exception:
        logger.exception('Exception when deleting testing_instance: %s', instance.name)


# This fixture must be named 'vm_name' because its tied to fixtures/virtual_machine
@pytest.fixture(scope="function")
def vm_name(testing_instance):
    # Pull it out of the testing instance
    return testing_instance.name


def wait_for_ui_state_refresh(instance, provider, state_change_time, timeout=900):
    """ Waits for 'State Changed On' refresh
    """
    def _wait_for_state_refresh():
        try:
            navigate_to(instance, 'Details')
            return state_change_time != instance.get_detail(properties=("Power Management",
                                                                        "State Changed On"))
        except NameError:
            logger.warning('NameError caught while waiting for state change, continuing')
            return False
    refresh_timer = RefreshTimer(time_for_refresh=180)
    try:
        wait_for(_wait_for_state_refresh, fail_func=lambda: provider.is_refreshed(refresh_timer),
                 num_sec=timeout, delay=30, message='Waiting for instance state refresh')
    except TimedOutError:
        return False


def wait_for_termination(provider, instance):
    """ Waits for VM/instance termination and refreshes power states and relationships
    """
    state_change_time = instance.get_detail(properties=('Power Management', 'State Changed On'))
    provider.refresh_provider_relationships()
    logger.info("Refreshing provider relationships and power states")
    refresh_timer = RefreshTimer(time_for_refresh=300)
    wait_for(provider.is_refreshed,
             [refresh_timer],
             message="Waiting for provider.is_refreshed",
             num_sec=1000,
             delay=60,
             handle_exception=True)
    wait_for_ui_state_refresh(instance, provider, state_change_time, timeout=720)
    if instance.get_detail(properties=('Power Management', 'Power State')) not in \
            {instance.STATE_TERMINATED, instance.STATE_ARCHIVED, instance.STATE_UNKNOWN}:
        """Wait for one more state change as transitional state also changes "State Changed On" time
        """
        logger.info("Instance is still powering down. please wait before termination")
        state_change_time = instance.get_detail(properties=('Power Management', 'State Changed On'))
        wait_for_ui_state_refresh(instance, provider, state_change_time, timeout=720)
    if provider.type == 'ec2':
        return True if provider.mgmt.is_vm_state(instance.name, provider.mgmt.states['deleted'])\
            else False
    elif instance.get_detail(properties=('Power Management', 'Power State')) in \
            {instance.STATE_TERMINATED, instance.STATE_ARCHIVED, instance.STATE_UNKNOWN}:
        return True
    else:
        logger.info("Instance is still running")
        return False


def check_power_options(soft_assert, instance, power_state):
    """ Checks if power options match given power state ('on', 'off')
    """
    for pwr_option in instance.ui_powerstates_available[power_state]:
        soft_assert(
            instance.is_pwr_option_available_in_cfme(option=pwr_option, from_details=True),
            "{} must be available in current power state - {} ".format(pwr_option, power_state))
    for pwr_option in instance.ui_powerstates_unavailable[power_state]:
        soft_assert(
            not instance.is_pwr_option_available_in_cfme(option=pwr_option, from_details=True),
            "{} must not be available in current power state - {} ".format(pwr_option, power_state))


def test_quadicon_terminate_cancel(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests terminate cancel

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE,
                                             cancel=True,
                                             from_details=False)
    soft_assert('currentstate-on' in testing_instance.find_quadicon().data['state'])


def test_quadicon_terminate(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests terminate instance

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE, from_details=False)
    logger.info("Terminate initiated")
    flash.assert_message_contain('Vm Destroy initiated')
    terminated_states = (testing_instance.STATE_TERMINATED, testing_instance.STATE_ARCHIVED,
                         testing_instance.STATE_UNKNOWN)
    soft_assert(testing_instance.wait_for_instance_state_change(desired_state=terminated_states,
                                                                timeout=1200))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_stop(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance stop

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.STOP)
    flash.assert_message_contain("Stop initiated")
    # Check Vm state in background
    wait_for(
        lambda: provider.mgmt.is_vm_stopped(testing_instance.name),
        num_sec=720,
        delay=20,
        message="mgmt system check - instance stopped")
    # Check Vm state in CFME
    soft_assert(testing_instance.wait_for_instance_state_change(
        desired_state=testing_instance.STATE_OFF, timeout=1200), "VM isn't stopped in CFME UI")


def test_start(provider, testing_instance, verify_vm_stopped, soft_assert):
    """ Tests instance start

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_OFF,
                                                    timeout=900)
    navigate_to(testing_instance, 'Details')
    testing_instance.power_control_from_cfme(option=testing_instance.START, cancel=False)
    flash.assert_message_contain("Start initiated")
    logger.info("Start initiated Flash message")
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


def test_soft_reboot(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance soft reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    state_change_time = testing_instance.get_detail(properties=('Power Management',
                                                                'State Changed On'))
    testing_instance.power_control_from_cfme(option=testing_instance.SOFT_REBOOT)
    flash.assert_message_contain('Restart Guest initiated')
    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    if provider.type == 'gce' \
            and testing_instance.get_detail(properties=('Power Management', 'Power State')) \
            == testing_instance.STATE_UNKNOWN:
        """Wait for one more state change as transitional state also
        changes "State Changed On" time on GCE provider
        """
        logger.info("Instance is still in \"{}\" state. please wait before CFME will show correct "
                    "state".format(testing_instance.get_detail(properties=('Power Management',
                                                                           'Power State'))))
        state_change_time = testing_instance.get_detail(properties=('Power Management',
                                                                    'State Changed On'))
        wait_for_ui_state_refresh(testing_instance, provider, state_change_time,
                                  timeout=720)

    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_hard_reboot(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance hard reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    navigate_to(testing_instance, 'Details')
    state_change_time = testing_instance.get_detail(properties=('Power Management',
                                                                'State Changed On'))

    testing_instance.power_control_from_cfme(option=testing_instance.HARD_REBOOT)
    flash.assert_message_contain("Reset initiated")

    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


@pytest.mark.uncollectif(lambda provider: (not provider.one_of(OpenStackProvider) and
                                           not provider.one_of(AzureProvider)))
def test_suspend(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance suspend

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.SUSPEND)
    flash.assert_message_contain("Suspend initiated")
    if provider.type == 'azure':
        provider.mgmt.wait_vm_suspended(testing_instance.name)
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_SUSPENDED)

    soft_assert(
        provider.mgmt.is_vm_suspended(testing_instance.name), "instance is still running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_unpause(provider, testing_instance, verify_vm_paused, soft_assert):
    """ Tests instance unpause

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_PAUSED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)
    flash.assert_message_contain("Start initiated")

    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)

    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


@pytest.mark.uncollectif(lambda provider: (not provider.one_of(OpenStackProvider) and
                                           not provider.one_of(AzureProvider)))
def test_resume(provider, testing_instance, verify_vm_suspended, soft_assert):
    """ Tests instance resume

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_SUSPENDED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)
    flash.assert_message_contain("Start initiated")
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)

    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


def test_terminate(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance terminate

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE)

    flash.assert_message_contain('Vm Destroy initiated')
    terminated_states = (testing_instance.STATE_TERMINATED, testing_instance.STATE_ARCHIVED,
            testing_instance.STATE_UNKNOWN)
    soft_assert(testing_instance.wait_for_instance_state_change(desired_state=terminated_states,
        timeout=1200))


def test_power_options_from_on(provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests available power options from ON state

    Metadata:
        test_flag: power_control
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    check_power_options(soft_assert, testing_instance, 'on')


def test_power_options_from_off(provider, testing_instance, verify_vm_stopped, soft_assert):
    """ Tests available power options from OFF state

    Metadata:
        test_flag: power_control
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_OFF,
                                                    timeout=1200)
    check_power_options(soft_assert, testing_instance, 'off')


class TestInstanceRESTAPI(object):
    """ Tests using the /api/instances collection. """
    def verify_vm_power_state(self, vm, state):
        vm.reload()
        if isinstance(state, (list, tuple)):
            return vm.power_state in state
        return vm.power_state == state

    def verify_action_result(self, rest_api, assert_success=True):
        assert rest_api.response.status_code == 200
        response = rest_api.response.json()
        if 'results' in response:
            response = response['results'][0]
        message = response['message']
        success = response['success']
        if assert_success:
            assert success
        return success, message

    @pytest.mark.uncollectif(lambda provider: provider.one_of(OpenStackProvider))
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_stop(self, setup_provider_funcscope, provider, testing_instance, verify_vm_running,
            soft_assert, appliance, from_detail):
        """ Tests instance stop

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()
        if from_detail:
            vm.action.stop()
        else:
            appliance.rest_api.collections.instances.action.stop(vm)
        self.verify_action_result(appliance.rest_api)
        wait_for(
            lambda: provider.mgmt.is_vm_stopped(testing_instance.name),
            num_sec=1200,
            delay=20,
            message="mgmt system check - instance stopped")
        soft_assert(not self.verify_vm_power_state(vm, testing_instance.STATE_ON),
            "instance still running")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_start(self, setup_provider_funcscope, provider, testing_instance, verify_vm_stopped,
            soft_assert, appliance, from_detail):
        """ Tests instance start

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(
            desired_state=testing_instance.STATE_OFF, timeout=1200)
        vm = testing_instance.get_vm_via_rest()
        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        self.verify_action_result(appliance.rest_api)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_ON),
            "instance not running")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_soft_reboot(self, setup_provider_funcscope, provider, testing_instance,
            soft_assert, verify_vm_running, appliance, from_detail):
        """ Tests instance soft reboot

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()
        if from_detail:
            vm.action.reboot_guest()
        else:
            appliance.rest_api.collections.instances.action.reboot_guest(vm)
        self.verify_action_result(appliance.rest_api)
        wait_for(lambda: vm.power_state != testing_instance.STATE_ON, num_sec=720, delay=45,
            fail_func=vm.reload)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_ON),
                    "instance not running")

    @pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_hard_reboot(self, setup_provider_funcscope, provider, testing_instance,
            soft_assert, verify_vm_running, appliance, from_detail):
        """ Tests instance hard reboot

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()
        if from_detail:
            vm.action.reset()
        else:
            appliance.rest_api.collections.instances.action.reset(vm)
        self.verify_action_result(appliance.rest_api)
        wait_for(lambda: vm.power_state != testing_instance.STATE_ON, num_sec=720, delay=45,
            fail_func=vm.reload)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_ON),
            "instance not running")

    @pytest.mark.uncollectif(lambda provider: not provider.one_of(AzureProvider, OpenStackProvider))
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_suspend_resume(self, setup_provider_funcscope, provider, testing_instance,
            soft_assert, verify_vm_running, appliance, from_detail):
        """ Tests instance suspend and resume

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()

        if from_detail:
            vm.action.suspend()
        else:
            appliance.rest_api.collections.instances.action.suspend(vm)
        self.verify_action_result(appliance.rest_api)
        testing_instance.wait_for_instance_state_change(
            desired_state=testing_instance.STATE_SUSPENDED)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_SUSPENDED),
            "instance not suspended")

        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        self.verify_action_result(appliance.rest_api)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_ON),
            "instance not running")

    @pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_pause_unpause(self, setup_provider_funcscope, provider, testing_instance,
            soft_assert, verify_vm_running, appliance, from_detail):
        """ Tests instance pause and unpause

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()

        if from_detail:
            vm.action.pause()
        else:
            appliance.rest_api.collections.instances.action.pause(vm)
        self.verify_action_result(appliance.rest_api)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_PAUSED)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_PAUSED),
            "instance not paused")

        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        self.verify_action_result(appliance.rest_api)
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        soft_assert(self.verify_vm_power_state(vm, testing_instance.STATE_ON),
            "instance not running")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_terminate(self, setup_provider_funcscope, provider, testing_instance,
            soft_assert, verify_vm_running, appliance, from_detail):
        """ Tests instance terminate via REST API

        Metadata:
            test_flag: power_control, provision, rest
        """
        testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.get_vm_via_rest()
        if from_detail:
            vm.action.terminate()
        else:
            appliance.rest_api.collections.instances.action.terminate(vm)
        self.verify_action_result(appliance.rest_api)
        terminated_states = (testing_instance.STATE_TERMINATED, testing_instance.STATE_ARCHIVED,
            testing_instance.STATE_UNKNOWN)
        soft_assert(testing_instance.wait_for_instance_state_change(desired_state=terminated_states,
            timeout=1200))
        soft_assert(self.verify_vm_power_state(vm, terminated_states), "instance not terminated")
