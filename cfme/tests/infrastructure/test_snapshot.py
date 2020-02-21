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
from cfme.utils.log_validator import LogValidator
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
def small_test_vm(setup_provider, provider, small_template, request):
    vm = provision_vm(provider, small_template)
    yield vm
    wait_for(lambda: vm.cleanup_on_provider, handle_exception=True, timeout=900)


@pytest.fixture(scope="function")
def full_test_vm(setup_provider, provider, full_template, request):
    vm = provision_vm(provider, full_template)
    yield vm
    vm.cleanup_on_provider()


def new_snapshot(test_vm, has_name=True, memory=False, create_description=True):
    name = fauxfactory.gen_alphanumeric(8)
    return InfraVm.Snapshot(
        name="test_snapshot_{}".format(name) if has_name else None,
        description="snapshot_{}".format(name) if create_description else None,
        memory=memory,
        parent_vm=test_vm
    )


@pytest.mark.rhv2
def test_memory_checkbox(small_test_vm, provider, soft_assert):
    """Tests snapshot memory checkbox

    Memory checkbox should be displayed and active when VM is running ('Power On').
    Memory checkbox should not be displayed when VM is stopped ('Power Off').

    Metadata:
        test_flag: power_control

    Polarion:
        assignee: prichard
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
@pytest.mark.rhv3
@test_requirements.rhev
@pytest.mark.meta(automates=[1571291, 1608475])
def test_snapshot_crud(small_test_vm, provider):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/6h
    """
    result = LogValidator(
        "/var/www/miq/vmdb/log/evm.log",
        failure_patterns=[r".*ERROR.*"],
    )
    result.start_monitoring()
    # has_name is false if testing RHEVMProvider
    snapshot = new_snapshot(small_test_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    # check for the size as "read" check
    if provider.appliance.version >= "5.11" and provider.one_of(RHEVMProvider):
        assert snapshot.size
    snapshot.delete()
    provider.refresh_provider_relationships(wait=600)
    assert result.validate(wait="60s")


@pytest.mark.rhv3
@test_requirements.rhev
@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[BZ(1443411)])
def test_delete_active_vm_snapshot(small_test_vm):
    """
    Check that it's not possible to delete an Active VM from RHV snapshots

    Bugzilla:
        1443411

    Polarion:
        assignee: anikifor
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    view = navigate_to(small_test_vm, 'SnapshotsAll')
    view.tree.click_path(small_test_vm.name, 'Active VM (Active)')
    assert not view.toolbar.delete.is_displayed


@pytest.mark.rhv3
@test_requirements.rhev
@pytest.mark.provider([RHEVMProvider])
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


@pytest.mark.provider([VMwareProvider])
def test_delete_all_snapshots(small_test_vm, provider):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
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


def verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event, request,
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
def test_verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event, request):
    """Tests revert snapshot

    Only valid for RHV 4+ providers, due to EOL we are not explicitly checking/blocking on this

    Metadata:
        test_flag: snapshot, provision

    Bugzilla:
        1561618

    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event, request)


@pytest.mark.provider([VMwareProvider])
def test_revert_active_snapshot(full_test_vm, provider, soft_assert, register_event, request):
    """Tests revert active snapshot

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event, request,
                           active_snapshot=True)


@pytest.mark.rhv2
@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[BZ(1552732)])
def test_revert_to_active_vm(small_test_vm, provider):
    """
    Test that it's not possible to revert to "Active VM" on RHV.

    Bugzilla:
        1552732

    Metadata:
        test_flag: snapshot

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    snapshot = new_snapshot(small_test_vm, has_name=False)
    snapshot.create()
    small_test_vm.power_control_from_cfme(option=small_test_vm.POWER_OFF, cancel=False)
    small_test_vm.wait_for_vm_state_change(desired_state=small_test_vm.STATE_OFF)
    snapshot.revert_to()
    view = navigate_to(small_test_vm, 'SnapshotsAll', force=True)
    view.tree.click_path(small_test_vm.name, snapshot.description, 'Active VM (Active)')
    assert not view.toolbar.revert.is_displayed


@pytest.mark.rhv3
@pytest.mark.provider([RHEVMProvider])
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
@pytest.mark.provider([VMwareProvider])
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
        assignee: prichard
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


@pytest.mark.provider([VMwareProvider])
def test_operations_suspended_vm(small_test_vm, soft_assert):
    """Tests snapshot operations on suspended vm

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/2h

    VirtualCenter 6.5 VMs are in suspended power state when reverted to a snapshot created in the
    suspended state.
    VirtualCenter 6.7 VMs are in off power state when reverted to a snapshot created in the
    suspended state.
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
    # Check VM state, VM should be suspended if VM version is 6.5
    # if version is 6.7 Vm state should be off (is_stopped)
    if small_test_vm.provider.version == 6.7:
        assert small_test_vm.mgmt.is_stopped
    else:
        assert small_test_vm.mgmt.is_suspended
    # Try to delete both snapshots while the VM is suspended
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.provider([VMwareProvider])
def test_operations_powered_off_vm(small_test_vm):
    """
    Polarion:
        assignee: prichard
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
        assignee: prichard
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


@pytest.mark.provider([VMwareProvider])
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
        assignee: prichard
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
    snap_name = fauxfactory.gen_alpha(start="snap_")
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


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_create_snapshot():
    """
    Snapshot can be created from VM details page, service details page
    and snapshot page.
    Check all pages and the snapshot count displayed on vm details page.

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        setup:
            1. Add an infra provider
            2. Create and order a service catalog which provisions a VM
            3. Login to SSUI
        testSteps:
            1. Test that snapshot can be created from Service Details page
                * Navigate to My Services -> <service_name>
                * Click Snapshots -> Create
                * Fill Name and click Create
            2. Test that snapshot can be created from VM Details page
                * Navigate to My Services -> <service_name> -> <vm_name>
                * Click Snapshots -> Create
                * Fill Name and click Create
            3. Test that snapshot can be created from Snapshot page
                * Navigate to My Services -> <service_name> -> <vm_name> -> Snapshots
                * Click Configuration -> Create Snapshot
                * Fill Name and click Create
        expectedResults:
            1. Snapshot successfully created
            2. Snapshot successfully created
            3. Snapshot successfully created
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_group_actions():
    """
    Test the SUI snapshot timeline.
    Test grouping of actions in a timeline. Try to create a couple of
    snapshots in a rapid succession, check how it looks in the timeline.

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add infra provider
        testSteps:
            1. create a new vm
            2. create multiple snapshots in fast succession (two should be enough)
            3. go to the VM details page, then Monitoring -> Timelines
            4. select "Management Events" and "Snapshot Activity" and click Apply
            5. click on the group of events in timeline
        expectedResults:
            1. vm created
            2. snapshots created
            3. timelines page displayed
            4. group of events displayed in the timeline
            5. details of events displayed, correct number of events
               displayed, time/date seems correct
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_new_vm():
    """
    Test the SUI snapshot timeline.
    See if there"s no timeline when there"s no snapshot.

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: low
        initialEstimate: 1/6h
        setup:
            1. Add infra provider
        testSteps:
            1. create a new vm
            2. go to the VM details page, then Monitoring -> Timelines
            3. select "Management Events" and "Snapshot Activity" and click Apply
        expectedResults:
            1. vm created
            2. timelines page displayed
            3. no timeline visible, warning "No records found for this timeline" displayed
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1600043])
def test_ssui_snapshot_memory_checkbox():
    """
    Test "snapshot vm memory" checkbox when creating snapshot for powered off vm.

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: medium
        initialEstimate: 1/4h
        setup:
            1. Add infra provider
            2. Create and order a service catalog which provisions a VM
            3. Power off testing VM
        testSteps:
            1. Via SSUI, test creating snapshot for powered off vm's
        expectedResults:
            1. "snapshot vm memory" checkbox should not be displayed.
    Bugzilla:
        1600043
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1398239])
def test_snapshot_tree_view_functionality():
    """
    Just test the snapshot tree view. Create a bunch of snapshots and see
    if the snapshot tree seems right. Check if the last created snapshot
    is active. Revert to some snapshot, then create another bunch of
    snapshots and check if the tree is correct.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        setup:
            1. Add infra provider
            2. Create testing VM
        testSteps:
            1. Create three snapshots
            2. Revert to second snapshot
            3. Create another two snapshots
        expectedResults:
            1. Snapshots created successfully; snapshot tree displays snapshots correctly;
               last created snapshot is Active
            2. Revert successful; snapshot tree displays snapshots correctly; active snapshot
               is the one we reverted to
            3. Snapshots created successfully; subtree in snapshots tree looks good; active
               snapshot is the last one created
    Bugzilla:
        1398239
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([VMwareProvider])
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1395116])
def test_snapshot_link_after_deleting_snapshot():
    """
    test snapshot link in vm summary page after deleting snapshot
    Have a vm, create couple of snapshots. Delete one snapshot. From the
    vm summary page use the history button and try to go back to
    snapshots. Go to the vm summary page again and try to click snapshots
    link, it should work.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        setup:
            1. Add vmware provider
            2. Create testing VM
        testSteps:
            1. Create two snapshots
            2. Delete one snapshot
            3. Use history button to navigate back to VM summary page
            4. From the vm summary page use the history button and try to go back to snapshots.
            5. From vm summary page click the snapshot link
        expectedResults:
            1. Snapshots successfully created
            2. Snapshot successfully deleted
            3. VM summary page displayed
            4. Snapshots page displayed
            5. Snapshots page displayed
    Bugzilla:
        1395116
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([VMwareProvider])
@test_requirements.ssui
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1490510])
def test_sui_snapshot_timeline_time_of_creation():
    """
    Timeline should display snapshots at the time of creation

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        setup:
            1. Add vmware provider
            2. Create testing VM
        testSteps:
            1. Create two snapshots
            2. Check the time of creation on the details page
            3. Check the time of creation on timeline
        expectedResults:
            1. Snapshots created successfully
            2. Snapshots time is correct
            3. Snapshots time is correct
    Bugzilla:
        1490510
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([VMwareProvider])
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_test_snapshot_count():
    """
    create few snapshots and check if the count displayed on service
    details page is same as the number of snapshots created
    and last snapshot created is displayed on service detail page .
    Also click on the snapshot link should navigate to snapshot page .

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
        setup:
            1. Add vmware provider
            2. Create testing VM
        testSteps:
            1. Create three snapshots
            2. Check the snapshot count displayed on service details page
            3. Check that last created snapshot is displayed on service defails page
            4. Click on that snapshot link
        expectedResults:
            1. Snapshots created successfully
            2. Count should be 3
            3. True
            4. Snapshot page displayed
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([VMwareProvider])
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_crud():
    """
    Test the SUI snapshot timeline.
    See if the data in the timeline are corresponding to the snapshot
    actions. Try to create snapshots, revert to snapshot and delete
    snapshot and see if the timeline reflects this correctly

    Polarion:
        assignee: prichard
        casecomponent: SelfServiceUI
        caseimportance: low
        initialEstimate: 1/2h
        setup:
            1. Add vmware provider
        testSteps:
            1. create a new vm
            2. create two snapshots for the VM
            3. revert to the first snapshot
            4. delete all snapshots
            5. go to the VM details page, then Monitoring -> Timelines
            6. select "Management Events" and "Snapshot Activity" and click Apply
        expectedResults:
            1. vm created
            2. snapshots created
            3. revert successful
            4. delete successful
            5. timelines page displayed
            6. snapshot timeline appears, all actions are in the timeline
               and visible, the time/date appears correct
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([VMwareProvider])
@pytest.mark.meta(coverage=[1419872])
def test_creating_second_snapshot_on_suspended_vm():
    """
    Test creating second snapshot on suspended vm.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Add vmware provider
            2. Create testing vm; suspend it
        testSteps:
            1. Take a first snapshot on suspended VM
            2. Take a second snapshot on suspended VM
        expectedResults:
            1. Snapshot created successfully
            2. Flash message Snapshot not taken since the state of the
               virtual machine has not changed since the last snapshot
               operation should be displayed in UI
    Bugzilla:
        1419872
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_verify_data():
    """
    Test the SUI snapshot timeline.
    See if data on the popup correspond to data shown below the timeline.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add infra provider
        testSteps:
            1. create a new vm
            2. create a snapshot
            3. go to the VM details page, then Monitoring -> Timelines
            4. select "Management Events" and "Snapshot Activity" and click Apply
            5. click on the event, compare data from the popup with data
               shown below the timeline
        expectedResults:
            1. vm created
            2. snapshot created
            3. timelines page displayed
            4. event displayed on timeline
            5. data should be identical
    """
    pass
