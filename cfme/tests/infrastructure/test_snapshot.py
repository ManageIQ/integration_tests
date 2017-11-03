# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import Vm  # For Vm.Snapshot
from cfme.utils import testgen
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.path import data_path
from cfme.utils.ssh import SSHClient
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.snapshot
]


pytest_generate_tests = testgen.generate([RHEVMProvider, VMwareProvider], scope="module")


@pytest.fixture(scope="module")
def domain(request, appliance):
    dom = DomainCollection(appliance).create(name=fauxfactory.gen_alpha(), enabled=True)
    request.addfinalizer(dom.delete_if_exists)
    return dom


def provision_vm(provider, template):
    vm_name = random_vm_name(context="snpst")
    vm = VM.factory(vm_name, provider, template_name=template.name)

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm


@pytest.yield_fixture(scope="module")
def small_test_vm(setup_provider_modscope, provider, small_template_modscope, request):
    vm = provision_vm(provider, small_template_modscope)
    yield vm

    try:
        vm.delete_from_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name, provider.name)


@pytest.yield_fixture(scope="module")
def full_test_vm(setup_provider_modscope, provider, full_template_modscope, request):
    vm = provision_vm(provider, full_template_modscope)
    yield vm

    try:
        vm.delete_from_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name, provider.name)


def new_snapshot(test_vm, has_name=True, memory=False):
    return Vm.Snapshot(
        name="snpshot_{}".format(fauxfactory.gen_alphanumeric(8)) if has_name else None,
        description="snapshot_{}".format(fauxfactory.gen_alphanumeric(8)),
        memory=memory, parent_vm=test_vm)


@pytest.mark.uncollectif(lambda provider:
                         (provider.one_of(RHEVMProvider) and provider.version < 4) or
                         current_version() < '5.8', 'Must be RHEVM provider version >= 4')
def test_memory_checkbox(small_test_vm, provider, soft_assert):
    # Make sure the VM is powered on
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_ON, cancel=False)
    # Try to create snapshot with memory on powered on VM
    has_name = not provider.one_of(RHEVMProvider)
    snapshot1 = new_snapshot(small_test_vm, has_name=has_name, memory=True)
    snapshot1.create()
    assert snapshot1.exists
    # Power off the VM
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_OFF, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_OFF)
    soft_assert(small_test_vm.provider.mgmt.is_vm_stopped(small_test_vm.name), "VM is not stopped!")
    # Try to create snapshot with memory on powered off VM
    snapshot2 = new_snapshot(small_test_vm, has_name=has_name, memory=True)
    try:
        snapshot2.create(force_check_memory=True)
    except NoSuchElementException:
        logger.info("Memory checkbox is not present on powered off VM.")
    # Make sure that snapshot with memory was not created
    wait_for(lambda: not snapshot2.exists, num_sec=40, delay=20, fail_func=provider.browser.refresh,
             handle_exception=True)


@pytest.mark.uncollectif(lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
                         'Must be RHEVM provider version >= 4')
def test_snapshot_crud(small_test_vm, provider):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision
    """
    # has_name is false if testing RHEVMProvider
    snapshot = new_snapshot(small_test_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    snapshot.delete()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider),
                         'Not VMware provider')
def test_delete_all_snapshots(small_test_vm, provider):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    snapshot2.delete_all()
    # Make sure the snapshots are indeed deleted
    wait_for(lambda: not snapshot1.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh)
    wait_for(lambda: not snapshot2.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh)


@pytest.mark.uncollectif(lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
                         'Must be RHEVM provider version >= 4')
def test_verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event):
    """Tests revert snapshot

    Metadata:
        test_flag: snapshot, provision
    """
    if provider.one_of(RHEVMProvider):
        snapshot1 = new_snapshot(full_test_vm, has_name=False)
    else:
        snapshot1 = new_snapshot(full_test_vm)
    full_template = getattr(provider.data.templates, 'full_template')
    ssh_kwargs = {
        'hostname': snapshot1.vm.provider.mgmt.get_ip_address(snapshot1.vm.name),
        'username': credentials[full_template.creds]['username'],
        'password': credentials[full_template.creds]['password']
    }
    ssh_client = SSHClient(**ssh_kwargs)
    # We need to wait for ssh to become available on the vm, it can take a while. Without
    # this wait, the ssh command would fail with 'port 22 not available' error.
    # Easiest way to solve this is just mask the exception with 'handle_exception = True'
    # and wait for successful completition of the ssh command.
    # The 'fail_func' ensures we close the connection that failed with exception.
    # Without this, the connection would hang there and wait_for would fail with timeout.
    wait_for(lambda: ssh_client.run_command('touch snapshot1.txt').rc == 0, num_sec=300,
             delay=20, handle_exception=True, fail_func=ssh_client.close())
    snapshot1.create()
    register_event(target_type='VmOrTemplate', target_name=full_test_vm.name,
                   event_type='vm_snapshot_complete')
    register_event(target_type='VmOrTemplate', target_name=full_test_vm.name,
                   event_type='vm_snapshot')
    ssh_client.run_command('touch snapshot2.txt')
    if provider.one_of(RHEVMProvider):
        snapshot2 = new_snapshot(full_test_vm, has_name=False)
    else:
        snapshot2 = new_snapshot(full_test_vm)
    snapshot2.create()

    if provider.one_of(RHEVMProvider):
        full_test_vm.power_control_from_cfme(option=full_test_vm.POWER_OFF, cancel=False)
        full_test_vm.wait_for_vm_state_change(
            desired_state=full_test_vm.STATE_OFF, timeout=900)

    snapshot1.revert_to()
    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=provider.browser.refresh)
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_OFF, timeout=720)
    full_test_vm.power_control_from_cfme(option=full_test_vm.POWER_ON, cancel=False)
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_ON, timeout=900)
    current_state = full_test_vm.find_quadicon().data['state']
    soft_assert(current_state.startswith('currentstate-on'),
                "Quadicon state is {}".format(current_state))
    soft_assert(full_test_vm.provider.mgmt.is_vm_running(full_test_vm.name), "vm not running")
    wait_for(lambda: ssh_client.run_command('test -e snapshot1.txt').rc == 0,
             num_sec=400, delay=20, handle_exception=True, fail_func=ssh_client.close())
    try:
        result = ssh_client.run_command('test -e snapshot1.txt')
        assert not result.rc
        result = ssh_client.run_command('test -e snapshot2.txt')
        assert result.rc
        logger.info('Revert to snapshot %s successful', snapshot1.name)
    except:
        logger.exception('Revert to snapshot %s Failed', snapshot1.name)
    ssh_client.close()


def setup_snapshot_env(test_vm, memory):
    logger.info("Starting snapshot setup")
    snapshot1 = new_snapshot(test_vm, memory=memory)
    snapshot1.create()
    snapshot2 = new_snapshot(test_vm, memory=memory)
    snapshot2.create()
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active,
             num_sec=300, delay=20, fail_func=test_vm.provider.browser.refresh)


@pytest.mark.parametrize("parent_vm", ["on_with_memory", "on_without_memory", "off"])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider),
                         'Not VMware provider')
def test_verify_vm_state_revert_snapshot(provider, parent_vm, small_test_vm):
    """
    test vm state after revert snapshot with parent vm:
     - powered on and includes memory
     - powered on without memory
     - powered off

    vm state after revert should be:
     - powered on
     - powered off
     - powered off
    """
    power = small_test_vm.POWER_ON if parent_vm.startswith('on') else small_test_vm.POWER_OFF
    memory = 'with_memory' in parent_vm

    small_test_vm.power_control_from_cfme(option=power, cancel=False)
    provider.mgmt.wait_vm_steady(small_test_vm.name)
    setup_snapshot_env(small_test_vm, memory)
    assert bool(small_test_vm.provider.mgmt.is_vm_running(small_test_vm.name)) == memory


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider),
                         'Not VMware provider')
def test_operations_suspended_vm(small_test_vm, soft_assert):
    """Tests snapshot operations on suspended vm

    Metadata:
        test_flag: snapshot, provision
    """
    # Create first snapshot when VM is running
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh)
    # Suspend the VM
    small_test_vm.power_control_from_cfme(option=small_test_vm.SUSPEND, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_SUSPENDED)
    current_state = small_test_vm.find_quadicon().data['state']
    soft_assert(current_state.startswith('currentstate-suspended'),
                "Quadicon state is {}".format(current_state))
    # Create second snapshot when VM is suspended
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh)
    # Try to revert to first snapshot while the VM is suspended
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh)
    # Check VM state, VM should be off
    current_state = small_test_vm.find_quadicon().data['state']
    soft_assert(current_state.startswith('currentstate-off'),
                "Quadicon state is {}".format(current_state))
    assert small_test_vm.provider.mgmt.is_vm_stopped(small_test_vm.name)
    # Revert back to second snapshot
    snapshot2.revert_to()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh)
    # Check VM state, VM should be suspended
    current_state = small_test_vm.find_quadicon().data['state']
    soft_assert(current_state.startswith('currentstate-suspended'),
                "Quadicon state is {}".format(current_state))
    assert small_test_vm.provider.mgmt.is_vm_suspended(small_test_vm.name)
    # Try to delete both snapshots while the VM is suspended
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider),
                         'Not VMware provider')
def test_operations_powered_off_vm(small_test_vm):
    # Make sure the VM is off
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_OFF, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_OFF)
    # Create first snapshot
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh)
    # Create second snapshot
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh)
    # Try to revert to first snapshot while the VM is off
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active is True, num_sec=300, delay=20, fail_func=snapshot1.refresh)
    # Try to delete both snapshots while the VM is off
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider),
                         'Not VMware provider')
def test_create_snapshot_via_ae(appliance, request, domain, small_test_vm):
    """This test checks whether the vm.create_snapshot works in AE.

    Prerequisities:
        * A VMware provider
        * A VM that has been discovered by CFME

    Steps:
        * Clone the Request class inside the System namespace into a new domain
        * Add a method named ``snapshot`` and insert the provided code there.
        * Add an instance named ``snapshot`` and set the methd from previous step
            as ``meth5``
        * Run the simulation of the method against the VM, preferably setting
            ``snap_name`` to something that can be checked
        * Wait until snapshot with such name appears.
    """
    # PREPARE
    file = data_path.join("ui").join("automate").join("test_create_snapshot_via_ae.rb")
    with file.open("r") as f:
        method_contents = f.read()
    miq_domain = DomainCollection(appliance).instantiate(name='ManageIQ')
    miq_class = miq_domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')
    miq_class.copy_to(domain)
    request_cls = domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')
    request.addfinalizer(request_cls.delete)
    method = request_cls.methods.create(name="snapshot", location='inline', script=method_contents)
    request.addfinalizer(method.delete)
    instance = request_cls.instances.create(
        name="snapshot",
        fields={
            "meth5": {
                'value': "snapshot"}})
    request.addfinalizer(instance.delete)

    # SIMULATE
    snap_name = fauxfactory.gen_alpha()
    snapshot = Vm.Snapshot(name=snap_name, parent_vm=small_test_vm)
    simulate(
        instance="Request",
        request="snapshot",
        target_type='VM and Instance',
        target_object=small_test_vm.name,
        execute_methods=True,
        attributes_values={"snap_name": snap_name})

    wait_for(lambda: snapshot.exists, timeout="2m", delay=10,
             fail_func=small_test_vm.provider.browser.refresh, handle_exception=True)

    # Clean up if it appeared
    snapshot.delete()
