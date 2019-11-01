# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.wait import RefreshTimer
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

FILTER_FIELDS = dict(required_fields=['test_power_control'])


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.long_running,
    test_requirements.power,
    pytest.mark.provider([CloudProvider], scope='function', **FILTER_FIELDS),
    pytest.mark.usefixtures('setup_provider'),
]


def create_instance(appliance, provider, template_name):
    instance = appliance.collections.cloud_instances.instantiate(random_vm_name('pwr-c'),
                                                                 provider,
                                                                 template_name)
    if not instance.exists_on_provider:
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    elif instance.provider.one_of(EC2Provider) and instance.mgmt.state == VmState.DELETED:
        instance.mgmt.rename('test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    return instance


@pytest.fixture(scope="function")
def testing_instance2(appliance, provider, small_template, setup_provider):
    """ Fixture to provision instance on the provider
    """
    instance2 = create_instance(appliance, provider, small_template.name)
    yield instance2
    instance2.cleanup_on_provider()


# This fixture must be named 'vm_name' because its tied to cfme/fixtures/virtual_machine
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


def wait_for_power_state_refresh(instance, state_change_time, timeout=720):
    return wait_for(
        lambda: instance.rest_api_entity.state_changed_on != state_change_time,
        num_sec=int(timeout),
        delay=30,
        message='Waiting for instance state refresh'
    ).out


def wait_for_termination(provider, instance):
    """ Waits for VM/instance termination and refreshes power states and relationships
    """
    view = navigate_to(instance, 'Details')
    pwr_mgmt = view.entities.summary('Power Management')
    state_change_time = pwr_mgmt.get_text_of('State Changed On')
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
    term_states = {instance.STATE_TERMINATED, instance.STATE_ARCHIVED, instance.STATE_UNKNOWN}
    if pwr_mgmt.get_text_of('Power State') not in term_states:
        """Wait for one more state change as transitional state also changes "State Changed On" time
        """
        logger.info("Instance is still powering down. please wait before termination")
        state_change_time = pwr_mgmt.get_text_of('State Changed On')
        wait_for_ui_state_refresh(instance, provider, state_change_time, timeout=720)

    return (instance.mgmt.state == VmState.DELETED
            if provider.one_of(EC2Provider)
            else pwr_mgmt.get_text_of('Power State') in term_states)


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


def wait_for_instance_state(soft_assert, instance, state):
    """
    Wait for VM to reach 'state' in both provider and on CFME UI

    'state' is a "friendly name" which is mapped to the proper instance state/provider state

    Args:
      soft_assert -- fixtures.soft_assert pytest fixture
      provider -- instance of CloudProvider
      instance -- instance of cfme.cloud.instance.Instance
      state -- str of either "started"/"running", "stopped", "suspended", "paused", or "terminated"
    """
    if state in ["started", "running"]:
        desired_mgmt_state = VmState.RUNNING
        desired_ui_state = instance.STATE_ON

    elif state == "stopped":
        desired_mgmt_state = VmState.STOPPED
        desired_ui_state = instance.STATE_OFF

    elif state == "suspended" and instance.mgmt.system.can_suspend:
        desired_mgmt_state = VmState.SUSPENDED
        desired_ui_state = instance.STATE_SUSPENDED

    elif state == "paused" and instance.mgmt.system.can_pause:
        desired_mgmt_state = VmState.PAUSED
        desired_ui_state = instance.STATE_PAUSED

    elif state == "terminated":
        # don't check state on the provider, since vm could be gone
        desired_mgmt_state = None
        desired_ui_state = (
            instance.STATE_TERMINATED,
            instance.STATE_ARCHIVED,
            instance.STATE_UNKNOWN
        )

    else:
        raise ValueError("Invalid instance state type of '{}' for provider '{}'"
                         .format(state, instance.provider))

    # Check VM state in provider
    if desired_mgmt_state:
        instance.mgmt.wait_for_state(desired_mgmt_state, timeout=720)

    # Check Vm state in CFME
    soft_assert(
        instance.wait_for_instance_state_change(desired_state=desired_ui_state, timeout=1200),
        "Instance {} isn't {} in CFME UI".format(instance, desired_ui_state)
    )


def test_quadicon_terminate_cancel(provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests terminate cancel

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE,
                                             cancel=True,
                                             from_details=False)
    soft_assert(testing_instance.find_quadicon().data['state'] == 'on')


def test_quadicon_terminate(appliance, provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests terminate instance

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE, from_details=False)
    logger.info("Terminate initiated")
    appliance.browser.create_view(BaseLoggedInPage).flash.assert_success_message(
        "Terminate initiated for 1 VM and Instance from the {} Database"
        .format(appliance.product_name)
    )

    soft_assert(
        testing_instance.wait_for_instance_state_change(
            desired_state=(
                testing_instance.STATE_TERMINATED,
                testing_instance.STATE_ARCHIVED,
                testing_instance.STATE_UNKNOWN
            ),
            timeout=1200
        )
    )


def test_stop(appliance, provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests instance stop

    Metadata:
        test_flag: power_control, provision

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.STOP)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Stop initiated', partial=True)

    wait_for_instance_state(soft_assert, testing_instance, state="stopped")


def test_start(appliance, provider, testing_instance, ensure_vm_stopped, soft_assert):
    """ Tests instance start

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_OFF,
                                                    timeout=900)
    navigate_to(testing_instance, 'Details')
    testing_instance.power_control_from_cfme(option=testing_instance.START, cancel=False)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Start initiated', partial=True)

    logger.info("Start initiated Flash message")
    wait_for_instance_state(soft_assert, testing_instance, state="started")


def test_soft_reboot(appliance, provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests instance soft reboot

    Metadata:
        test_flag: power_control, provision

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    view = navigate_to(testing_instance, 'Details')
    pwr_mgmt = view.entities.summary('Power Management')
    state_change_time = pwr_mgmt.get_text_of('State Changed On')

    testing_instance.power_control_from_cfme(option=testing_instance.SOFT_REBOOT)
    view.flash.assert_success_message(text='Restart Guest initiated', partial=True)
    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    pwr_state = pwr_mgmt.get_text_of('Power State')

    if provider.one_of(GCEProvider) and pwr_state == testing_instance.STATE_UNKNOWN:
        """Wait for one more state change as transitional state also
        changes "State Changed On" time on GCE provider
        """
        logger.info("Instance is still in \"{}\" state. please wait before CFME will show correct "
                    "state".format(pwr_state))
        state_change_time = pwr_mgmt.get_text_of('State Changed On')
        wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)

    wait_for_instance_state(soft_assert, testing_instance, state="started")


def test_power_on_or_off_multiple(provider, testing_instance, testing_instance2, soft_assert):
    """
    Verify that multiple instances can be selected and powered on/off

    Metadata:
        test_flag: power_control, provision

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/8h
    """
    # The instances *should* be on after provisioning... but we'll make sure here...
    testing_instance.mgmt.ensure_state(VmState.RUNNING)
    testing_instance2.mgmt.ensure_state(VmState.RUNNING)
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance2.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)

    def _get_view_with_icons_checked():
        view = navigate_to(testing_instance.parent, 'All')
        view.toolbar.view_selector.select('Grid View')
        view.paginator.set_items_per_page(1000)
        view.entities.get_entity(name=testing_instance.name).check()
        view.entities.get_entity(name=testing_instance2.name).check()
        return view

    # Power 2 instances off
    view = _get_view_with_icons_checked()
    view.toolbar.power.item_select(testing_instance.STOP, handle_alert=True)
    view.flash.assert_success_message(text='Stop initiated for 2 VMs and Instances', partial=True)
    wait_for_instance_state(soft_assert, testing_instance, state="stopped")
    wait_for_instance_state(soft_assert, testing_instance2, state="stopped")

    # Power 2 instances on
    view = _get_view_with_icons_checked()
    view.toolbar.power.item_select(testing_instance.START, handle_alert=True)
    view.flash.assert_success_message(text='Start initiated for 2 VMs and Instances', partial=True)
    wait_for_instance_state(soft_assert, testing_instance, state="started")
    wait_for_instance_state(soft_assert, testing_instance2, state="started")


@pytest.mark.provider([OpenStackProvider],
                      scope='function', override=True, **FILTER_FIELDS)
def test_hard_reboot(appliance, provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests instance hard reboot

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    view = navigate_to(testing_instance, 'Details')
    state_change_time = view.entities.summary('Power Management').get_text_of('State Changed On')

    testing_instance.power_control_from_cfme(option=testing_instance.HARD_REBOOT)

    view.flash.assert_success_message(text='Reset initiated', partial=True)

    wait_for_ui_state_refresh(testing_instance, provider, state_change_time, timeout=720)
    wait_for_instance_state(soft_assert, testing_instance, state="started")


@pytest.mark.provider([AzureProvider],
                      scope='function', override=True, **FILTER_FIELDS)
def test_hard_reboot_unsupported(appliance, testing_instance):
    """
    Tests that hard reboot throws an 'unsupported' error message on an Azure instance

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.power_control_from_cfme(option=testing_instance.HARD_REBOOT,
                                             from_details=False)
    # power_control_from_cfme navigated
    message = (
        "Reset does not apply to at least one of the selected items"
        if appliance.version < "5.10"
        else "Reset action does not apply to selected items"
    )
    appliance.browser.create_view(BaseLoggedInPage).flash.assert_message(message)


@pytest.mark.provider([AzureProvider, OpenStackProvider],
                      scope='function', override=True, **FILTER_FIELDS)
def test_suspend(appliance, provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests instance suspend

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.SUSPEND)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text='Suspend initiated', partial=True)

    if provider.one_of(AzureProvider):
        testing_instance.mgmt.wait_for_state(VmState.SUSPENDED)
    wait_for_instance_state(soft_assert, testing_instance, state="suspended")


@pytest.mark.provider([OpenStackProvider],
                      scope='function', override=True, **FILTER_FIELDS)
def test_unpause(appliance, provider, testing_instance, ensure_vm_paused, soft_assert):
    """ Tests instance unpause

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_PAUSED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)

    appliance.browser.create_view(BaseLoggedInPage).flash.assert_success_message(
        text='Start initiated', partial=True)

    wait_for_instance_state(soft_assert, testing_instance, state="started")


@pytest.mark.provider([AzureProvider, OpenStackProvider],
                      scope='function', override=True, **FILTER_FIELDS)
def test_resume(appliance, provider, testing_instance, ensure_vm_suspended, soft_assert):
    """ Tests instance resume

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_SUSPENDED)
    testing_instance.power_control_from_cfme(option=testing_instance.START)

    appliance.browser.create_view(BaseLoggedInPage).flash.assert_success_message(
        text='Start initiated', partial=True)

    wait_for_instance_state(soft_assert, testing_instance, state="started")


def test_terminate(provider, testing_instance, ensure_vm_running, soft_assert, appliance):
    """Tests instance terminate

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE)
    appliance.browser.create_view(BaseLoggedInPage).flash.assert_success_message(
        "Terminate initiated for 1 VM and Instance from the {} Database"
        .format(appliance.product_name)
    )
    wait_for_instance_state(soft_assert, testing_instance, state="terminated")


def test_instance_power_options_from_on(provider, testing_instance, ensure_vm_running, soft_assert):
    """ Tests available power options from ON state

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/10h
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_ON)
    check_power_options(soft_assert, testing_instance, 'on')


def test_instance_power_options_from_off(provider, testing_instance,
                                         ensure_vm_stopped, soft_assert):
    """Tests available power options from OFF state

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/10h
        caseimportance: high
        tags: power
    """
    testing_instance.wait_for_instance_state_change(desired_state=testing_instance.STATE_OFF,
                                                    timeout=1200)
    check_power_options(soft_assert, testing_instance, 'off')


@test_requirements.rest
class TestInstanceRESTAPI(object):
    """ Tests using the /api/instances collection. """

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_stop(self, provider, testing_instance, ensure_vm_running,
            soft_assert, appliance, from_detail):
        """ Tests instance stop

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity
        if from_detail:
            vm.action.stop()
        else:
            appliance.rest_api.collections.instances.action.stop(vm)
        assert_response(appliance.rest_api)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_OFF
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="stopped")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_start(self, provider, testing_instance, ensure_vm_stopped,
            soft_assert, appliance, from_detail):
        """ Tests instance start

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_OFF, timeout=1200)
        vm = testing_instance.rest_api_entity
        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        assert_response(appliance.rest_api)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_ON
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="started")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_soft_reboot(self, provider, testing_instance,
            soft_assert, ensure_vm_running, appliance, from_detail):
        """ Tests instance soft reboot

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity
        state_change_time = vm.state_changed_on
        if from_detail:
            vm.action.reboot_guest()
        else:
            appliance.rest_api.collections.instances.action.reboot_guest(vm)
        assert_response(appliance.rest_api)

        # On some providers the VM never actually shuts off, on others it might
        # We may also miss a quick reboot during the wait_for.
        # Just check for when the state last changed
        wait_for_power_state_refresh(testing_instance, state_change_time)
        state_change_time = testing_instance.rest_api_entity.state_changed_on
        # If the VM is not on after this state change, wait for another
        if vm.power_state != testing_instance.STATE_ON:
            wait_for_power_state_refresh(testing_instance, state_change_time)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_ON
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="started")

    @pytest.mark.provider([OpenStackProvider],
                          scope='function', override=True, **FILTER_FIELDS)
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_hard_reboot(self, provider, testing_instance,
            soft_assert, ensure_vm_running, appliance, from_detail):
        """ Tests instance hard reboot

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity
        if from_detail:
            vm.action.reset()
        else:
            appliance.rest_api.collections.instances.action.reset(vm)
        assert_response(appliance.rest_api)
        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_ON,
            timeout=720
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="started")

    @pytest.mark.provider([AzureProvider, OpenStackProvider],
                          scope='function', override=True, **FILTER_FIELDS)
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_suspend_resume(self, provider, testing_instance,
            soft_assert, ensure_vm_running, appliance, from_detail):
        """ Tests instance suspend and resume

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity

        if from_detail:
            vm.action.suspend()
        else:
            appliance.rest_api.collections.instances.action.suspend(vm)
        assert_response(appliance.rest_api)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_SUSPENDED,
            delay=15
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="suspended")

        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        assert_response(appliance.rest_api)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_ON,
            delay=15
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="started")

    @pytest.mark.provider([OpenStackProvider],
                          scope='function', override=True, **FILTER_FIELDS)
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_pause_unpause(self, provider, testing_instance,
            soft_assert, ensure_vm_running, appliance, from_detail):
        """ Tests instance pause and unpause

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity

        if from_detail:
            vm.action.pause()
        else:
            appliance.rest_api.collections.instances.action.pause(vm)
        assert_response(appliance.rest_api)
        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_PAUSED,
            delay=15
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="paused")

        if from_detail:
            vm.action.start()
        else:
            appliance.rest_api.collections.instances.action.start(vm)
        assert_response(appliance.rest_api)

        # assert and wait until the power state change is reflected in REST
        assert testing_instance.wait_for_power_state_change_rest(
            desired_state=testing_instance.STATE_ON,
            delay=15
        )
        # check if the power state change is reflected on UI and provider
        wait_for_instance_state(soft_assert, testing_instance, state="started")

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_terminate(self, provider, testing_instance,
            soft_assert, ensure_vm_running, appliance, from_detail):
        """ Tests instance terminate via REST API

        Metadata:
            test_flag: power_control, provision, rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: high
            initialEstimate: 1/4h
        """
        testing_instance.wait_for_power_state_change_rest(desired_state=testing_instance.STATE_ON)
        vm = testing_instance.rest_api_entity
        if from_detail:
            vm.action.terminate()
        else:
            appliance.rest_api.collections.instances.action.terminate(vm)
        assert_response(appliance.rest_api)

        wait_for_instance_state(soft_assert, testing_instance, state="terminated")

        terminated_states = (
            testing_instance.STATE_TERMINATED,
            testing_instance.STATE_ARCHIVED,
            testing_instance.STATE_UNKNOWN
        )
        vm.reload()
        soft_assert(vm.power_state in terminated_states, "instance not terminated")


@pytest.mark.meta(automates=[1701188, 1655477, 1686015, 1738584])
def test_power_options_on_archived_instance_all_page(testing_instance):
    """This test case is to check Power option drop-down button is disabled on archived and orphaned
       instances all page. Also it performs the power operations on instance and checked expected
       flash messages.
       Note: Cloud instances can not be orphaned

    Bugzilla:
        1701188
        1655477
        1686015
        1738584

    Polarion:
        assignee: ghubale
        initialEstimate: 1/2h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Control
        tags: power
        testSteps:
            1. Add provider cloud provider
            2. Navigate to Archived instance all page
            3. Select any instance and click on power option drop-down
    """
    testing_instance.mgmt.delete()
    testing_instance.wait_for_instance_state_change(desired_state="archived", timeout=1200)
    cloud_instance = testing_instance.appliance.collections.cloud_instances
    view = navigate_to(cloud_instance, 'ArchivedAll')

    # Selecting particular archived instance
    testing_instance.find_quadicon(from_archived_all=True).check()

    # After selecting particular archived instance; 'Power' drop down gets enabled.
    # Reading all the options available in 'power' drop down
    for action in view.toolbar.power.items:
        if action == "Resume" and BZ(1738584, forced_streams=['5.10', '5.11']).blocks:
            continue

        # Performing power actions on archived instance
        view.toolbar.power.item_select(action, handle_alert=True)
        if action == 'Soft Reboot':
            action = 'Restart Guest'
        elif action == 'Hard Reboot':
            action = 'Reset'
        elif action == 'Delete':
            action = 'Terminate'
        view.flash.assert_message(f'{action} action does not apply to selected items')
        view.flash.dismiss()
