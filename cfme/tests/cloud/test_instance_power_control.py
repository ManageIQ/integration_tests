# -*- coding: utf-8 -*-
import fauxfactory
import cfme.web_ui.flash as flash
import pytest
from cfme.cloud.instance import instance_factory, get_all_instances, EC2Instance, OpenStackInstance
from cfme.fixtures import pytest_selenium as sel
from utils import error, testgen
from utils.wait import wait_for, TimedOutError

pytestmark = [pytest.mark.usefixtures('test_power_control')]


def pytest_generate_tests(metafunc):
    final_argv, final_argn, final_ids = [], [], []

    if 'ec2_only' in metafunc.fixturenames:
        prov_types = ['ec2']
    elif 'openstack_only' in metafunc.fixturenames:
        prov_types = ['openstack']
    else:
        prov_types = ['ec2', 'openstack']

    # Get all providers and pick those, that have power control test enabled
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, prov_types, 'test_power_control')
    if not idlist:
        return
    for argn, argv, single_id in zip(argnames, argvalues, idlist):
        test_pwr_ctl_i = argnames.index('test_power_control')
        provider_key_i = argnames.index('provider_key')
        final_argn = argnames
        if argv[test_pwr_ctl_i] is True:
            final_argv.append(argv)
            final_ids.append(argv[provider_key_i])

    # Then append '{provider_type}_only' fixture, if necessary
    if len(prov_types) == 1:
        final_argn.append('{}_only'.format(prov_types[0]))
        for argval in final_argv:
            argval.append('')

    testgen.parametrize(metafunc, final_argn, final_argv, ids=final_ids, scope="function")


# This fixture must be named 'vm_name' because its tied to fixtures/virtual_machine
@pytest.fixture(scope="module")
def vm_name():
    return "test_instance_pwrctl_{}".format(fauxfactory.gen_alphanumeric(8))


@pytest.fixture(scope="function")
def test_instance(request, delete_instances_fin, setup_provider,
                  provider_crud, provider_mgmt, vm_name):
    """ Fixture to provision instance on the provider
    """
    instance = instance_factory(vm_name, provider_crud)
    if not provider_mgmt.does_vm_exist(vm_name):
        delete_instances_fin[provider_crud.key] = instance
        instance.create_on_provider()
    elif isinstance(instance, EC2Instance) and \
            provider_mgmt.is_vm_state(vm_name, provider_mgmt.states['deleted']):
        provider_mgmt.set_name(
            vm_name, 'test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        delete_instances_fin[provider_crud.key] = instance
        instance.create_on_provider()
    return instance


@pytest.fixture(scope="module")
def delete_instances_fin(request):
    """ Fixture to add a finalizer to delete provisioned instances at the end of tests

    This is a "trashbin" fixture - it returns a mutable that you put stuff into.
    """
    provisioned_instances = {}

    def delete_instances(instances_dict):
        for instance in instances_dict.itervalues():
            instance.delete_from_provider()
    request.addfinalizer(lambda: delete_instances(provisioned_instances))
    return provisioned_instances


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
def test_quadicon_terminate_cancel(setup_provider_funcscope, provider_type, provider_mgmt,
                                   test_instance, verify_vm_running, soft_assert):
    """ Tests terminate cancel

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720)
    test_instance.power_control_from_cfme(option=test_instance.TERMINATE, cancel=True)
    with error.expected('instance still exists'):
        # try to find VM, if found, try again - times out with expected message
        wait_for(
            lambda: provider_mgmt.does_vm_exist(test_instance.name),
            fail_condition=True,
            num_sec=60,
            delay=15,
            message="instance still exists")
    soft_assert(test_instance.find_quadicon().state == 'currentstate-on')


@pytest.mark.long_running
def test_quadicon_terminate(setup_provider_funcscope, provider_type, provider_mgmt,
                            test_instance, verify_vm_running, soft_assert):
    """ Tests terminate instance

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720)
    test_instance.power_control_from_cfme(option=test_instance.TERMINATE, cancel=False)
    wait_for(test_instance.does_vm_exist_in_cfme, fail_condition=True, num_sec=300, delay=30,
        fail_func=test_instance.provider_crud.refresh_provider_relationships,
        message="instance still exists in cfme UI")
    if provider_type == 'openstack':
        soft_assert(not provider_mgmt.does_vm_exist(test_instance.name), "instance still exists")
    else:
        soft_assert(
            provider_mgmt.is_vm_state(test_instance.name, provider_mgmt.states['deleted']),
            "instance still exists")
    sel.force_navigate("clouds_instances_archived_branch")
    soft_assert(
        test_instance.name in get_all_instances(do_not_navigate=True),
        "instance is not among archived instances")


@pytest.mark.long_running
def test_stop(ec2_only, setup_provider_funcscope, provider_type, provider_mgmt,
              test_instance, soft_assert, verify_vm_running):
    """ Tests instance stop

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    check_power_options(soft_assert, test_instance, 'on')
    test_instance.power_control_from_cfme(
        option=test_instance.STOP, cancel=False, from_details=True)
    flash.assert_message_contain("Stop initiated")
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_OFF, timeout=720, from_details=True)
    wait_for(
        lambda: provider_mgmt.is_vm_stopped(test_instance.name),
        num_sec=180,
        delay=20,
        message="mgmt system check - instance stopped")


@pytest.mark.long_running
def test_start(ec2_only, setup_provider_funcscope, provider_type, provider_mgmt,
               test_instance, soft_assert, verify_vm_stopped):
    """ Tests instance start

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_OFF, timeout=720, from_details=True)
    check_power_options(soft_assert, test_instance, 'off')
    test_instance.power_control_from_cfme(
        option=test_instance.START, cancel=False, from_details=True)
    flash.assert_message_contain("Start initiated")
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    soft_assert(
        provider_mgmt.is_vm_running(test_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_soft_reboot(setup_provider_funcscope, provider_type, provider_mgmt,
                     test_instance, soft_assert, verify_vm_running):
    """ Tests instance soft reboot

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    state_change_time = test_instance.get_detail(('Power Management', 'State Changed On'))
    test_instance.power_control_from_cfme(
        option=test_instance.SOFT_REBOOT, cancel=False, from_details=True)
    flash.assert_message_contain("Restart initiated")
    wait_for_state_change_time_refresh(test_instance, state_change_time, timeout=720)
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, from_details=True)
    soft_assert(
        provider_mgmt.is_vm_running(test_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_hard_reboot(openstack_only, setup_provider_funcscope, provider_type,
                     provider_mgmt, test_instance, soft_assert, verify_vm_running):
    """ Tests instance hard reboot

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    state_change_time = test_instance.get_detail(('Power Management', 'State Changed On'))
    test_instance.power_control_from_cfme(
        option=test_instance.HARD_REBOOT, cancel=False, from_details=True)
    flash.assert_message_contain("Reset initiated")
    wait_for_state_change_time_refresh(test_instance, state_change_time, timeout=720)
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, from_details=True)
    soft_assert(
        provider_mgmt.is_vm_running(test_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_suspend(openstack_only, setup_provider_funcscope, provider_type, provider_mgmt,
                 test_instance, soft_assert, verify_vm_running):
    """ Tests instance suspend

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    check_power_options(soft_assert, test_instance, 'on')
    test_instance.power_control_from_cfme(
        option=test_instance.SUSPEND, cancel=False, from_details=True)
    flash.assert_message_contain("Suspend initiated")
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_OFF, timeout=720, from_details=True)
    soft_assert(
        provider_mgmt.is_vm_suspended(test_instance.name),
        "instance is still running")


@pytest.mark.long_running
@pytest.mark.meta(blockers=[1183757])
def test_resume(openstack_only, setup_provider_funcscope,
        provider_type, provider_mgmt, test_instance, soft_assert, verify_vm_suspended):
    """ Tests instance resume

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_SUSPENDED, timeout=720, from_details=True)
    check_power_options(soft_assert, test_instance, 'off')
    test_instance.power_control_from_cfme(
        option=test_instance.START, cancel=False, from_details=True)
    flash.assert_message_contain("Start initiated")
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    soft_assert(
        provider_mgmt.is_vm_running(test_instance.name),
        "instance is not running")


@pytest.mark.long_running
def test_terminate(setup_provider_funcscope,
        provider_type, provider_mgmt, test_instance, soft_assert, verify_vm_running):
    """ Tests instance terminate

    Metadata:
        test_flag: power_control, provision
    """
    test_instance.wait_for_vm_state_change(
        desired_state=test_instance.STATE_ON, timeout=720, from_details=True)
    test_instance.power_control_from_cfme(
        option=test_instance.TERMINATE, cancel=False, from_details=True)
    flash.assert_message_contain("Terminate initiated")
    wait_for(test_instance.does_vm_exist_in_cfme, fail_condition=True, num_sec=300, delay=30,
        fail_func=test_instance.provider_crud.refresh_provider_relationships,
        message="VM no longer exists in cfme UI")
    if provider_type == 'openstack':
        soft_assert(not provider_mgmt.does_vm_exist(test_instance.name), "instance still exists")
    else:
        soft_assert(
            provider_mgmt.is_vm_state(test_instance.name, provider_mgmt.states['deleted']),
            "instance still exists")
    sel.force_navigate("clouds_instances_archived_branch")
    soft_assert(
        test_instance.name in get_all_instances(do_not_navigate=True),
        "instance is not among archived instances")
