# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.infrastructure.virtual_machines import InfraVmSnapshotAddView
from cfme.infrastructure.virtual_machines import InfraVmSnapshotView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.path import data_path
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.snapshot,
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module"),
]


def provision_vm(provider, template):
    vm_name = random_vm_name(context="snpst")
    vm = provider.appliance.collections.infra_vms.instantiate(vm_name,
                                                              provider,
                                                              template.name)

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm


@pytest.fixture(scope="function")
def small_test_vm(setup_provider, provider, small_template):
    vm = provision_vm(provider, small_template)
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture(scope="function")
def full_test_vm(setup_provider, provider, full_template):
    vm = provision_vm(provider, full_template)
    yield vm
    vm.cleanup_on_provider()


def new_snapshot(test_vm, has_name=True, memory=False, create_description=True):
    name = fauxfactory.gen_alphanumeric(8)
    return InfraVm.Snapshot(
        name="snpshot_{}".format(name) if has_name else None,
        description="snapshot_{}".format(name) if create_description else None,
        memory=memory,
        parent_vm=test_vm
    )


@pytest.mark.rhv2
@pytest.mark.uncollectif(lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
                         'Must be RHEVM provider version >= 4')
def test_memory_checkbox(small_test_vm, provider, soft_assert):
    """Tests snapshot memory checkbox

    Memory checkbox should be displayed and active when VM is running ('Power On').
    Memory checkbox should not be displayed when VM is stopped ('Power Off').

    Metadata:
        test_flag: power_control

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
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
    soft_assert(small_test_vm.mgmt.is_stopped, "VM is not stopped!")
    # Check that checkbox is not displayed
    view = navigate_to(small_test_vm, 'SnapshotsAdd')
    assert not view.snapshot_vm_memory.is_displayed, (
        "Memory checkbox is displayed when VM is stopped")


@pytest.mark.rhv1
@pytest.mark.uncollectif(lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
                         'Must be RHEVM provider version >= 4')
def test_snapshot_crud(small_test_vm, provider):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/6h
    """
    # has_name is false if testing RHEVMProvider
    snapshot = new_snapshot(small_test_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    snapshot.delete()


@pytest.mark.rhv3
@pytest.mark.provider([RHEVMProvider], override=True)
def test_create_without_description(small_test_vm):
    """
    Test that we get an error message when we try to create a snapshot with
    blank description on RHV provider.

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    if small_test_vm.appliance.version >= '5.10':
        # In 5.10 it's not possible to create a snapshot w/o description,"Create" button is disabled
        view = navigate_to(small_test_vm, 'SnapshotsAdd')
        assert view.create.disabled
    else:
        snapshot = new_snapshot(small_test_vm, has_name=False, create_description=False)
        with pytest.raises(AssertionError):
            snapshot.create()
        view = snapshot.parent_vm.create_view(InfraVmSnapshotAddView)
        view.flash.assert_message('Description is required')


@pytest.mark.provider([VMwareProvider], override=True)
def test_delete_all_snapshots(small_test_vm, provider):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    snapshot2.delete_all()
    # Make sure the snapshots are indeed deleted
    wait_for(lambda: not snapshot1.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for first snapshot to disappear")
    wait_for(lambda: not snapshot2.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for second snapshot to disappear")


def verify_revert_snapshot(full_test_vm, provider, soft_assert,
                           active_snapshot=False):
    if provider.one_of(RHEVMProvider):
        # RHV snapshots have only description, no name
        snapshot1 = new_snapshot(full_test_vm, has_name=False)
    else:
        snapshot1 = new_snapshot(full_test_vm)
    full_template = getattr(provider.data.templates, 'full_template')
    # Define parameters of the ssh connection
    ssh_kwargs = {
        'hostname': snapshot1.parent_vm.mgmt.ip,
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
    wait_for(lambda: ssh_client.run_command('touch snapshot1.txt').success, num_sec=400,
             delay=20, handle_exception=True, fail_func=ssh_client.close(),
             message="Waiting for successful SSH connection")
    # Create first snapshot
    snapshot1.create()
    ssh_client.run_command('touch snapshot2.txt')

    # If we are not testing 'revert to active snapshot' situation, we create another snapshot
    if not active_snapshot:
        if provider.one_of(RHEVMProvider):
            snapshot2 = new_snapshot(full_test_vm, has_name=False)
        else:
            snapshot2 = new_snapshot(full_test_vm)
        snapshot2.create()

    # VM on RHV provider must be powered off before snapshot revert
    if provider.one_of(RHEVMProvider):
        full_test_vm.power_control_from_cfme(option=full_test_vm.POWER_OFF, cancel=False)
        full_test_vm.wait_for_vm_state_change(
            desired_state=full_test_vm.STATE_OFF, timeout=900)

    snapshot1.revert_to()
    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=provider.browser.refresh,
             message="Waiting for the first snapshot to become active")
    # VM state after revert should be OFF
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_OFF, timeout=720)
    # Let's power it ON again
    full_test_vm.power_control_from_cfme(option=full_test_vm.POWER_ON, cancel=False)
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_ON, timeout=900)
    soft_assert(full_test_vm.mgmt.is_running, "vm not running")
    # Wait for successful ssh connection
    wait_for(lambda: ssh_client.run_command('test -e snapshot1.txt').success,
             num_sec=400, delay=10, handle_exception=True, fail_func=ssh_client.close(),
             message="Waiting for successful SSH connection after revert")
    try:
        result = ssh_client.run_command('test -e snapshot1.txt')
        assert result.success  # file found, RC=0
        result = ssh_client.run_command('test -e snapshot2.txt')
        assert result.failed  # file not found, RC=1
        logger.info('Revert to snapshot %s successful', snapshot1.name)
    except Exception:
        logger.exception('Revert to snapshot %s Failed', snapshot1.name)
    ssh_client.close()


@pytest.mark.rhv1
@pytest.mark.meta(
    blockers=[
        BZ(
            1561618,
            forced_streams=['5.8', '5.9'],
            unblock=lambda provider: not provider.one_of(RHEVMProvider)
        )
    ]
)
@pytest.mark.uncollectif(lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
                         'Must be RHEVM provider version >= 4')
def test_verify_revert_snapshot(full_test_vm, provider, soft_assert):
    """Tests revert snapshot

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    verify_revert_snapshot(full_test_vm, provider, soft_assert)


@pytest.mark.provider([VMwareProvider], override=True)
def test_revert_active_snapshot(full_test_vm, provider, soft_assert):
    """Tests revert active snapshot

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    verify_revert_snapshot(full_test_vm, provider, soft_assert,
                           active_snapshot=True)


@pytest.mark.rhv3
@pytest.mark.provider([RHEVMProvider], override=True)
@pytest.mark.meta(automates=[BZ(1375544)])
def test_revert_on_running_vm(small_test_vm):
    """
    Test that revert button is not clickable on powered on VM.

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    snapshot = new_snapshot(small_test_vm, has_name=False)
    snapshot.create()
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_ON, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_ON)
    with pytest.raises(Exception, match='Could not find an element'):
        snapshot.revert_to()


def setup_snapshot_env(test_vm, memory):
    logger.info("Starting snapshot setup")
    snapshot1 = new_snapshot(test_vm, memory=memory)
    snapshot1.create()
    snapshot2 = new_snapshot(test_vm, memory=memory)
    snapshot2.create()
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active,
             num_sec=300, delay=20, fail_func=test_vm.provider.browser.refresh,
             message="Waiting for the first snapshot to become active")


@pytest.mark.parametrize("parent_vm", ["on_with_memory", "on_without_memory", "off"])
@pytest.mark.provider([VMwareProvider], override=True)
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

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    power = small_test_vm.POWER_ON if parent_vm.startswith('on') else small_test_vm.POWER_OFF
    memory = 'with_memory' in parent_vm

    small_test_vm.power_control_from_cfme(option=power, cancel=False)
    small_test_vm.mgmt.wait_for_steady_state()
    setup_snapshot_env(small_test_vm, memory)
    assert bool(small_test_vm.mgmt.is_running) == memory


@pytest.mark.provider([VMwareProvider], override=True)
def test_operations_suspended_vm(small_test_vm, soft_assert):
    """Tests snapshot operations on suspended vm

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/2h
    """
    # Create first snapshot when VM is running
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active")
    # Suspend the VM
    small_test_vm.mgmt.ensure_state(VmState.SUSPENDED)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_SUSPENDED)
    # Create second snapshot when VM is suspended
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh,
             message="Waiting for the second snapshot to become active")
    # Try to revert to first snapshot while the VM is suspended
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active after revert")
    # Check VM state, VM should be off
    assert small_test_vm.mgmt.is_stopped
    # Revert back to second snapshot
    snapshot2.revert_to()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh,
             message="Waiting for the second snapshot to become active after revert")
    # Check VM state, VM should be suspended
    assert small_test_vm.mgmt.is_suspended
    # Try to delete both snapshots while the VM is suspended
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.provider([VMwareProvider], override=True)
def test_operations_powered_off_vm(small_test_vm):
    """
    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/2h
    """
    # Make sure the VM is off
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_OFF, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_OFF)
    # Create first snapshot
    snapshot1 = new_snapshot(small_test_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active")
    # Create second snapshot
    snapshot2 = new_snapshot(small_test_vm)
    snapshot2.create()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh,
             message="Waiting for the second snapshot to become active")
    # Try to revert to first snapshot while the VM is off
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active is True, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the fist snapshot to become active after revert")
    # Try to delete both snapshots while the VM is off
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.rhv3
def test_snapshot_history_btn(small_test_vm, provider):
    """Tests snapshot history button
    Metadata:
        test_flag: snapshot

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
    """
    snapshot = new_snapshot(small_test_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    vm_details_view = navigate_to(small_test_vm, 'Details')
    item = '"Snapshots" for Virtual Machine "{}"'.format(small_test_vm.name)
    vm_details_view.toolbar.history.item_select(item)
    snapshot_view = small_test_vm.create_view(InfraVmSnapshotView)
    assert snapshot_view.is_displayed


@pytest.mark.provider([VMwareProvider], override=True)
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

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
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
    snapshot = InfraVm.Snapshot(name=snap_name, parent_vm=small_test_vm)
    simulate(
        appliance=appliance,
        instance="Request",
        request="snapshot",
        target_type='VM and Instance',
        target_object=small_test_vm.name,
        execute_methods=True,
        attributes_values={"snap_name": snap_name})

    wait_for(lambda: snapshot.exists, timeout="2m", delay=10,
             fail_func=small_test_vm.provider.browser.refresh, handle_exception=True,
             message="Waiting for snapshot create")

    # Clean up if it appeared
    snapshot.delete()
