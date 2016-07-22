# -*- coding: utf-8 -*-
import fauxfactory
import cfme.web_ui.flash as flash
import pytest
from cfme.cloud.instance import (EC2Instance, Instance, OpenStackInstance,
                                 AzureInstance, get_all_instances)
from cfme.fixtures import pytest_selenium as sel
from utils import error, testgen, version
from utils.blockers import GH
from utils.log import logger
from utils.wait import wait_for, TimedOutError


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['azure', 'ec2', 'openstack'], required_fields=[('test_power_control', True)])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="function")

pytestmark = [pytest.mark.tier(2)]


@pytest.fixture(scope="function")
def testing_instance(request, setup_provider, provider):
    """ Fixture to provision instance on the provider
    """
    instance = Instance.factory("test_inst_pwrctl_{}".format(fauxfactory.gen_alpha(8)), provider)
    if not provider.mgmt.does_vm_exist(instance.name):
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
        request.addfinalizer(instance.delete_from_provider)
    elif instance.provider.type == "ec2" and \
            provider.mgmt.is_vm_state(instance.name, provider.mgmt.states['deleted']):
        provider.mgmt.set_name(
            instance.name, 'test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
        request.addfinalizer(instance.delete_from_provider)
    return instance


# This fixture must be named 'vm_name' because its tied to fixtures/virtual_machine
@pytest.fixture(scope="function")
def vm_name(testing_instance):
    # Pull it out of the testing instance
    return testing_instance.name


def wait_for_state_change_time_refresh(instance, state_change_time, timeout=300):
    """ Waits for 'State Changed On' refresh
    """
    def _wait_for_state_refresh():
        instance.load_details()
        return state_change_time != instance.get_detail(
            properties=("Power Management", "State Changed On"))

    try:
        wait_for(_wait_for_state_refresh, num_sec=timeout, delay=30)
    except TimedOutError:
        return False


def check_power_options(soft_assert, instance, power_state):
    """ Checks if power options match given power state ('on', 'off')
    """
    must_be_available = {
        AzureInstance: {
            'on': [AzureInstance.STOP, AzureInstance.SUSPEND, AzureInstance.TERMINATE],
            'off': [AzureInstance.START, AzureInstance.TERMINATE]
        },
        EC2Instance: {
            'on': [EC2Instance.STOP, EC2Instance.SOFT_REBOOT, EC2Instance.TERMINATE],
            'off': [EC2Instance.START, EC2Instance.TERMINATE]
        },
        OpenStackInstance: {
            'on': [
                OpenStackInstance.SUSPEND,
                OpenStackInstance.SOFT_REBOOT,
                OpenStackInstance.HARD_REBOOT,
                OpenStackInstance.TERMINATE
            ],
            'off': [OpenStackInstance.START, OpenStackInstance.TERMINATE]
        }
    }
    mustnt_be_available = {
        AzureInstance: {
            'on': [AzureInstance.START],
            'off': [AzureInstance.STOP, AzureInstance.SUSPEND, AzureInstance.SOFT_REBOOT]
        },
        EC2Instance: {
            'on': [EC2Instance.START],
            'off': [EC2Instance.STOP, EC2Instance.SOFT_REBOOT]
        },
        OpenStackInstance: {
            'on': [OpenStackInstance.START],
            'off': [
                OpenStackInstance.SUSPEND,
                OpenStackInstance.SOFT_REBOOT,
                OpenStackInstance.HARD_REBOOT
            ]
        }
    }

    for pwr_option in must_be_available[instance.__class__][power_state]:
        soft_assert(
            instance.is_pwr_option_available_in_cfme(option=pwr_option, from_details=True),
            "{} must be available in current power state".format(pwr_option))
    for pwr_option in mustnt_be_available[instance.__class__][power_state]:
        soft_assert(
            not instance.is_pwr_option_available_in_cfme(option=pwr_option, from_details=True),
            "{} must not be available in current power state".format(pwr_option))


@pytest.mark.long_running
def test_quadicon_terminate_cancel(setup_provider_funcscope, provider, testing_instance,
                                   verify_vm_running, soft_assert):
    """ Tests terminate cancel

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE, cancel=True)
    with error.expected('instance still exists'):
        # try to find VM, if found, try again - times out with expected message
        wait_for(
            lambda: provider.mgmt.does_vm_exist(testing_instance.name),
            fail_condition=True,
            num_sec=60,
            delay=15,
            message="instance still exists")
    soft_assert('currentstate-on' in testing_instance.find_quadicon().state)


@pytest.mark.long_running
def test_quadicon_terminate(setup_provider_funcscope, provider, testing_instance,
                            verify_vm_running, soft_assert):
    """ Tests terminate instance

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720)
    testing_instance.power_control_from_cfme(option=testing_instance.TERMINATE, cancel=False)
    testing_instance.wait_to_disappear(timeout=300)
    if provider.type == 'openstack':
        soft_assert(not testing_instance.does_vm_exist_on_provider(), "instance still exists")
    else:
        soft_assert(
            provider.mgmt.is_vm_state(testing_instance.name, provider.mgmt.states['deleted']),
            "instance still exists")
    sel.force_navigate("clouds_instances_archived_branch")
    soft_assert(
        testing_instance.name in get_all_instances(do_not_navigate=True),
        "instance is not among archived instances")


@pytest.mark.long_running
@pytest.mark.uncollectif(lambda provider: provider.type != 'ec2' and provider.type != 'azure')
def test_stop(setup_provider_funcscope, provider, testing_instance, soft_assert, verify_vm_running):
    """ Tests instance stop

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    check_power_options(soft_assert, testing_instance, 'on')
    logger.info("Begin Power Control Stop \n")
    testing_instance.power_control_from_cfme(
        option=testing_instance.STOP, cancel=False, from_details=True)
    flash.assert_message_contain("Stop initiated")
    logger.info("Stop initiated Flash message\n")
    if provider.type == 'azure':
        provider.mgmt.wait_vm_stopped(testing_instance.name)
        logger.info("Just waited for wait_vm_stopped to avoid state change confusion")
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_OFF, timeout=720, from_details=True)
    logger.info("Waiting for VM State Change \n")
    wait_for(
        lambda: provider.mgmt.is_vm_stopped(testing_instance.name),
        num_sec=180,
        delay=20,
        message="mgmt system check - instance stopped")


@pytest.mark.long_running
def test_start(
        setup_provider_funcscope, provider, testing_instance, soft_assert, verify_vm_stopped):
    """ Tests instance start

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_OFF, timeout=720, from_details=True)
    check_power_options(soft_assert, testing_instance, 'off')
    testing_instance.power_control_from_cfme(
        option=testing_instance.START, cancel=False, from_details=True)
    flash.assert_message_contain("Start initiated")
    logger.info("Start initiated Flash message\n")
    if provider.type == 'azure':
        provider.mgmt.wait_vm_running(testing_instance.name)
        logger.info("Just waited for wait_vm_running to avoid state change confusion")
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    logger.info("Waiting for VM State Change \n")
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_soft_reboot(setup_provider_funcscope, provider, testing_instance, soft_assert,
                     verify_vm_running):
    """ Tests instance soft reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    state_change_time = testing_instance.get_detail(('Power Management', 'State Changed On'))
    testing_instance.power_control_from_cfme(
        option=testing_instance.SOFT_REBOOT, cancel=False, from_details=True)
    flash.assert_message_contain(version.pick({
        version.LOWEST: "Restart initiated",
        "5.5": "Restart Guest initiated"}))
    wait_for_state_change_time_refresh(testing_instance, state_change_time, timeout=720)
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, from_details=True)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.long_running
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack' and provider.type != 'azure')
def test_hard_reboot(setup_provider_funcscope, provider, testing_instance, soft_assert,
                     verify_vm_running):
    """ Tests instance hard reboot

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    state_change_time = testing_instance.get_detail(('Power Management', 'State Changed On'))
    testing_instance.power_control_from_cfme(
        option=testing_instance.HARD_REBOOT, cancel=False, from_details=True)
    flash.assert_message_contain("Reset initiated")
    wait_for_state_change_time_refresh(testing_instance, state_change_time, timeout=720)
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, from_details=True)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.long_running
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack' and provider.type != 'azure')
def test_suspend(
        setup_provider_funcscope, provider, testing_instance, soft_assert, verify_vm_running):
    """ Tests instance suspend

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    check_power_options(soft_assert, testing_instance, 'on')
    testing_instance.power_control_from_cfme(
        option=testing_instance.SUSPEND, cancel=False, from_details=True)
    flash.assert_message_contain("Suspend initiated")
    if provider.type == 'azure':
        provider.mgmt.wait_vm_suspended(testing_instance.name)
        logger.info("Just waited for wait_vm_suspended to avoid state change confusion")
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_SUSPENDED, timeout=720, from_details=True)
    soft_assert(
        provider.mgmt.is_vm_suspended(testing_instance.name),
        "instance is still running")


@pytest.mark.long_running
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack' and provider.type != 'azure')
def test_unpause(
        setup_provider_funcscope, provider, testing_instance, soft_assert, verify_vm_paused):
    """ Tests instance unpause

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_PAUSED, timeout=720, from_details=True)
    check_power_options(soft_assert, testing_instance, 'off')
    testing_instance.power_control_from_cfme(
        option=testing_instance.START, cancel=False, from_details=True)
    flash.assert_message_contain("Start initiated")
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.long_running
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack' and provider.type != 'azure')
def test_resume(setup_provider_funcscope, provider, testing_instance, soft_assert,
                verify_vm_suspended):
    """ Tests instance resume

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_SUSPENDED, timeout=720, from_details=True)
    check_power_options(soft_assert, testing_instance, 'off')
    testing_instance.power_control_from_cfme(
        option=testing_instance.START, cancel=False, from_details=True)
    flash.assert_message_contain("Start initiated")
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    soft_assert(
        provider.mgmt.is_vm_running(testing_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_terminate(setup_provider_funcscope, provider, testing_instance, soft_assert,
                   verify_vm_running):
    """ Tests instance terminate

    Metadata:
        test_flag: power_control, provision
    """
    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    testing_instance.power_control_from_cfme(
        option=testing_instance.TERMINATE, cancel=False, from_details=True)
    flash.assert_message_contain({
        version.LOWEST: "Terminate initiated",
        "5.5": "Vm Destroy initiated"})
    testing_instance.wait_to_disappear(timeout=600)
    if provider.type == 'openstack':
        soft_assert(not testing_instance.does_vm_exist_on_provider(), "instance still exists")
    else:
        soft_assert(
            provider.mgmt.is_vm_state(testing_instance.name, provider.mgmt.states['deleted']),
            "instance still exists")
    sel.force_navigate("clouds_instances_archived_branch")
    soft_assert(
        testing_instance.name in get_all_instances(do_not_navigate=True),
        "instance is not among archived instances")


@pytest.mark.ignore_stream("5.4")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_terminate_via_rest(setup_provider_funcscope, provider, testing_instance, soft_assert,
        verify_vm_running, rest_api, from_detail):
    assert "terminate" in rest_api.collections.instances.action.all
    if provider.type == 'ec2' and GH("ManageIQ/manageiq:6955").blocks:
        pytest.skip("Termination ec2 is blocked by""manageiq/issues/6955")

    testing_instance.wait_for_vm_state_change(
        desired_state=testing_instance.STATE_ON, timeout=720, from_details=True)
    vm = rest_api.collections.instances.get(name=testing_instance.name)
    if from_detail:
        vm.action.terminate()
    else:
        rest_api.collections.instances.action.terminate(vm)
    if provider.type == 'openstack':
        testing_instance.wait_to_disappear(timeout=800)
        soft_assert(not testing_instance.does_vm_exist_on_provider(), "instance still exists")
    else:
        wait_for(lambda: vm.power_state == testing_instance.STATE_TERMINATED,
            num_sec=600, delay=10, fail_func=vm.reload)
    # Bug https://bugzilla.redhat.com/show_bug.cgi?id=1310067
    # That's why we skip soft_assert for aws
    if provider.type != 'ec2':
        sel.force_navigate("clouds_instances_archived_branch")
        soft_assert(
            testing_instance.name in get_all_instances(do_not_navigate=True),
            "instance is not among archived instances")
