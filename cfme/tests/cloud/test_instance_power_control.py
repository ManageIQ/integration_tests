# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
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
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    elif instance.provider.type == "ec2" and \
            provider.mgmt.is_vm_state(instance.name, provider.mgmt.states['deleted']):
        provider.mgmt.set_name(
            instance.name, 'test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)

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
    view = navigate_to(instance, 'Details')

    def _wait_for_state_refresh():
        try:
            state = view.entities.summary('Power Management').get_text_of('State Changed On')
            return state_change_time != state
        except NameError:
            logger.warning('NameError caught while waiting for state change, continuing')
            return False

    refresh_timer = RefreshTimer(time_for_refresh=180)

    def _fail_func():
        provider.is_refreshed(refresh_timer)
        view.toolbar.reload.click()

    try:
        wait_for(_wait_for_state_refresh, fail_func=_fail_func,
                 num_sec=timeout, delay=30, message='Waiting for instance state refresh')
    except TimedOutError:
        return False


def wait_for_termination(provider, instance):
    """ Waits for VM/instance termination and refreshes power states and relationships
    """
    view = navigate_to(instance, 'Details')
    state_change_time = view.entities.summary('Power Management').get_text_of('State Changed On')
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
    if view.entities.summary('Power Management').get_text_of('Power State') not in \
            {instance.STATE_TERMINATED, instance.STATE_ARCHIVED, instance.STATE_UNKNOWN}:
        """Wait for one more state change as transitional state also changes "State Changed On" time
        """
        logger.info("Instance is still powering down. please wait before termination")
        state_change_time = view.entities.summary('Power Management').get_text_of(
            'State Changed On')
        wait_for_ui_state_refresh(instance, provider, state_change_time, timeout=720)
    if provider.type == 'ec2':
        return provider.mgmt.is_vm_state(instance.name, provider.mgmt.states['deleted'])
    elif view.entities.summary('Power Management').get_text_of('Power State') in \
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


def test_quadicon_terminate(appliance, provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests terminate instance

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE, from_details=False)
    logger.info("Terminate initiated")
    msg_part = "Terminate initiated" if appliance.version >= '5.9' else "Vm Destroy initiated"
    msg = "{} for 1 VM and Instance from the {} Database".format(msg_part, appliance.product_name)
    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(msg)
    terminated_states = (testing_instance.STATE_TERMINATED, testing_instance.STATE_ARCHIVED,
                         testing_instance.STATE_UNKNOWN)
    soft_assert(testing_instance.wait_for_instance_state_change(desired_state=terminated_states,
                                                                timeout=1200))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_stop(appliance, provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance stop

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.STOP)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Stop initiated', partial=True)

    # Check Vm state in background
    wait_for(
        lambda: provider.mgmt.is_vm_stopped(testing_instance.name),
        num_sec=720,
        delay=20,
        message="mgmt system check - instance stopped")
    # Check Vm state in CFME
    soft_assert(testing_instance.wait_for_instance_state_change(
        desired_state=testing_instance.STATE_OFF, timeout=1200), "VM isn't stopped in CFME UI")


def test_start(appliance, provider, testing_instance, verify_vm_stopped, soft_assert):
    """ Tests instance start

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_OFF,
                                                    timeout=900)
    navigate_to(testing_instance, 'Details')
    testing_instance.power_control_from_cfme(option=testing_instance.START, cancel=False)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Start initiated', partial=True)

    logger.info("Start initiated Flash message")
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


def test_soft_reboot(appliance, provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance soft reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    view = navigate_to(testing_instance, 'Details')
    state_change_time = view.entities.summary('Power Management').get_text_of('State Changed On')
    testing_instance.power_control_from_cfme(option=testing_instance.SOFT_REBOOT)
    view.flash.assert_success_message(text='Restart Guest initiated', partial=True)
    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    pwr_state = view.entities.summary('Power Management').get_text_of('Power State')
    if provider.type == 'gce' and pwr_state == testing_instance.STATE_UNKNOWN:
        """Wait for one more state change as transitional state also
        changes "State Changed On" time on GCE provider
        """
        logger.info("Instance is still in \"{}\" state. please wait before CFME will show correct "
                    "state".format(pwr_state))
        state_change_time = view.entities.summary('Power Management').get_text_of(
            'State Changed On')
        wait_for_ui_state_refresh(testing_instance, provider, state_change_time,
                                  timeout=720)

    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_hard_reboot(appliance, provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance hard reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    view = navigate_to(testing_instance, 'Details')
    state_change_time = view.entities.summary('Power Management').get_text_of('State Changed On')

    testing_instance.power_control_from_cfme(option=testing_instance.HARD_REBOOT)

    view.flash.assert_success_message(text='Reset initiated', partial=True)

    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    soft_assert(provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(AzureProvider))
def test_hard_reboot_unsupported(appliance, provider, testing_instance):
    """
    Tests that hard reboot throws an 'unsupported' error message on an Azure instance

    Metadata:
        test_flag: power_control, provision
    """
    view = navigate_to(testing_instance, 'All')
    testing_instance.power_control_from_cfme(
        option=testing_instance.HARD_REBOOT, from_details=False)
    assert len(view.flash.messages) > 0, "Expected a flash error message to be displayed"

    error_msg_found = False
    # Message we are looking for is...
    #   "Reset does not apply to at least one of the selected items"
    # ...but we leave out 'Reset' in case that text changes in the future
    txt = "does not apply to at least one of the selected items"
    for message in view.flash.messages:
        if txt in message.read():
            error_msg_found = True

    assert error_msg_found, ("Expected to see error containing text '{}' after "
                             "attempting unsupported hard reboot".format(txt))


@pytest.mark.uncollectif(lambda provider: (not provider.one_of(OpenStackProvider) and
                                           not provider.one_of(AzureProvider)))
def test_suspend(appliance, provider, testing_instance, verify_vm_running, soft_assert):
    """ Tests instance suspend

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.SUSPEND)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Suspend initiated', partial=True)

    if provider.type == 'azure':
        provider.mgmt.wait_vm_suspended(testing_instance.name)
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_SUSPENDED)

    soft_assert(
        provider.mgmt.is_vm_suspended(testing_instance.name), "instance is still running")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_unpause(appliance, provider, testing_instance, verify_vm_paused, soft_assert):
    """ Tests instance unpause

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_PAUSED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Start initiated', partial=True)

    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)

    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


@pytest.mark.uncollectif(lambda provider: (not provider.one_of(OpenStackProvider) and
                                           not provider.one_of(AzureProvider)))
def test_resume(appliance, provider, testing_instance, verify_vm_suspended, soft_assert):
    """ Tests instance resume

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_SUSPENDED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Start initiated', partial=True)

    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)

    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name), "instance is not running")


def test_terminate(provider, testing_instance, verify_vm_running, soft_assert, appliance):
    """ Tests instance terminate

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE)

    msg_part = "Terminate initiated" if appliance.version >= '5.9' else "Vm Destroy initiated"
    msg = "{} for 1 VM and Instance from the {} Database".format(msg_part, appliance.product_name)
    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(msg)
    terminated_states = (
        testing_instance.STATE_TERMINATED, testing_instance.STATE_ARCHIVED,
        testing_instance.STATE_UNKNOWN
    )
    soft_assert(
        testing_instance.wait_for_instance_state_change(
            desired_state=terminated_states, timeout=1200
        )
    )


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
