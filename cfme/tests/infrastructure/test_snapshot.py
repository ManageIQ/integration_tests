from contextlib import closing

import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.base.credential import SSHCredential
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.infrastructure.virtual_machines import InfraVmSnapshotAddView
from cfme.infrastructure.virtual_machines import InfraVmSnapshotView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.path import data_path
from cfme.utils.ssh import connect_ssh
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.snapshot,
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module"),
]


def new_snapshot(test_vm, has_name=True, memory=False, create_description=True):
    name = fauxfactory.gen_alphanumeric(8)
    return InfraVm.Snapshot(
        name=f"test_snapshot_{name}" if has_name else None,
        description=f"snapshot_{name}" if create_description else None,
        memory=memory,
        parent_vm=test_vm
    )


def test_memory_checkbox(create_vm, provider, soft_assert):
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
    create_vm.power_control_from_cfme(option=create_vm.POWER_ON, cancel=False)
    # Try to create snapshot with memory on powered on VM
    has_name = not provider.one_of(RHEVMProvider)
    snapshot1 = new_snapshot(create_vm, has_name=has_name, memory=True)
    snapshot1.create()
    assert snapshot1.exists
    # Power off the VM
    create_vm.power_control_from_cfme(option=create_vm.POWER_OFF, cancel=False)
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_OFF)
    soft_assert(create_vm.mgmt.is_stopped, "VM is not stopped!")
    # Check that checkbox is not displayed
    view = navigate_to(create_vm, 'SnapshotsAdd')
    assert not view.snapshot_vm_memory.is_displayed, (
        "Memory checkbox is displayed when VM is stopped")


@test_requirements.rhev
@pytest.mark.meta(automates=[1571291, 1608475])
def test_snapshot_crud(create_vm, provider):
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
    snapshot = new_snapshot(create_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    # check for the size as "read" check
    if provider.appliance.version >= "5.11" and provider.one_of(RHEVMProvider):
        assert snapshot.size
    snapshot.delete()
    provider.refresh_provider_relationships(wait=600)
    assert result.validate(wait="60s")


@test_requirements.rhev
@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[BZ(1443411)])
def test_delete_active_vm_snapshot(create_vm):
    """
    Check that it's not possible to delete an Active VM from RHV snapshots

    Bugzilla:
        1443411

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    view = navigate_to(create_vm, 'SnapshotsAll')
    view.tree.click_path(create_vm.name, 'Active VM (Active)')
    assert not view.toolbar.delete.is_displayed


@test_requirements.rhev
@pytest.mark.provider([RHEVMProvider])
def test_create_without_description(create_vm):
    """
    Test that we get an error message when we try to create a snapshot with
    blank description on RHV provider.

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    if create_vm.appliance.version >= '5.10':
        # In 5.10 it's not possible to create a snapshot w/o description,"Create" button is disabled
        view = navigate_to(create_vm, 'SnapshotsAdd')
        assert view.create.disabled
    else:
        snapshot = new_snapshot(create_vm, has_name=False, create_description=False)
        with pytest.raises(AssertionError):
            snapshot.create()
        view = snapshot.parent_vm.create_view(InfraVmSnapshotAddView)
        view.flash.assert_message('Description is required')


@pytest.mark.provider([VMwareProvider])
def test_delete_all_snapshots(create_vm, provider):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    snapshot1 = new_snapshot(create_vm)
    snapshot1.create()
    snapshot2 = new_snapshot(create_vm)
    snapshot2.create()
    snapshot2.delete_all()
    # Make sure the snapshots are indeed deleted
    wait_for(lambda: not snapshot1.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for first snapshot to disappear")
    wait_for(lambda: not snapshot2.exists, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for second snapshot to disappear")


def verify_revert_snapshot(full_test_vm, provider, soft_assert, register_event, request,
                           active_snapshot=False):
    SSH_READY_TIMEOUT = 300
    if provider.one_of(RHEVMProvider):
        # RHV snapshots have only description, no name
        snapshot1 = new_snapshot(full_test_vm, has_name=False)
    else:
        snapshot1 = new_snapshot(full_test_vm)
    full_template = getattr(provider.data.templates, 'full_template')
    creds = SSHCredential.from_config(full_template.creds)

    # We need to wait for ssh to become available on the vm, it can take a while.
    # connect_ssh will iterate over "all_ips" on the VM and return a client when it can connect

    with closing(connect_ssh(full_test_vm.mgmt, creds, num_sec=SSH_READY_TIMEOUT)) as ssh_client:
        ssh_client.run_command('touch snapshot1.txt')
        # Create first snapshot
        snapshot1.create()

        # Assuming creating snapshot shouldn't break the ssh connection...
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
            desired_state=full_test_vm.STATE_OFF, timeout=400)

    snapshot1.revert_to()
    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(lambda: snapshot1.active, num_sec=700, delay=30, fail_func=provider.browser.refresh,
             message="Waiting for the first snapshot to become active")
    # VM state after revert should be OFF
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_OFF, timeout=720)
    # Let's power it ON again
    full_test_vm.power_control_from_cfme(option=full_test_vm.POWER_ON, cancel=False)
    full_test_vm.wait_for_vm_state_change(desired_state=full_test_vm.STATE_ON, timeout=400)
    soft_assert(full_test_vm.mgmt.is_running, "vm not running")
    # Wait for successful ssh connection
    with closing(connect_ssh(full_test_vm.mgmt, creds, num_sec=SSH_READY_TIMEOUT)) as ssh_client:
        assert ssh_client.run_command('test -e snapshot1.txt').success
        # This checks the exit status is 1 -- file doesn't exist.
        assert ssh_client.run_command('test -e snapshot2.txt') == 1


@pytest.mark.uncollectif(lambda provider: provider.one_of(RHEVMProvider),
                        reason="RHV providers blocked for BZ 1805803 marked WONTFIX")
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_verify_revert_snapshot(create_vm, provider, soft_assert, register_event, request):
    """Tests revert snapshot

    Only valid for RHV 4+ providers, due to EOL we are not explicitly checking/blocking on this

    Metadata:
        test_flag: snapshot, provision

    Bugzilla:
        1805803

    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    # getting the initial value for OS details.
    view = navigate_to(create_vm, 'Details')
    os_text_initial = view.entities.summary('Properties').get_text_of('Operating System')
    verify_revert_snapshot(create_vm, provider, soft_assert, register_event, request)
    # verify that the system info is displayed
    view = navigate_to(create_vm, 'Details')
    # check that the OS is in the field.
    os_text_compare = view.entities.summary('Properties').get_text_of('Operating System')
    assert os_text_compare == os_text_initial
    os_view = navigate_to(create_vm, 'OS Info')
    # check that the OS Info view is displayed and contains OS data
    assert os_view.is_displayed
    os_text_compare = view.entities.summary('Basic Information').get_text_of('Operating System')
    assert os_text_compare == os_text_initial


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
@pytest.mark.provider([VMwareProvider])
def test_revert_active_snapshot(create_vm, provider, soft_assert, register_event, request):
    """Tests revert active snapshot

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    verify_revert_snapshot(create_vm, provider, soft_assert, register_event, request,
                           active_snapshot=True)


@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[BZ(1552732)])
def test_revert_to_active_vm(create_vm, provider):
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
    snapshot = new_snapshot(create_vm, has_name=False)
    snapshot.create()
    create_vm.power_control_from_cfme(option=create_vm.POWER_OFF, cancel=False)
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_OFF)
    snapshot.revert_to()
    view = navigate_to(create_vm, 'SnapshotsAll', force=True)
    view.tree.click_path(create_vm.name, snapshot.description, 'Active VM (Active)')
    assert not view.toolbar.revert.is_displayed


@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[BZ(1375544)])
def test_revert_on_running_vm(create_vm):
    """
    Test that revert button is not clickable on powered on VM.

    Metadata:
        test_flag: snapshot, provision

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    snapshot = new_snapshot(create_vm, has_name=False)
    snapshot.create()
    create_vm.power_control_from_cfme(option=create_vm.POWER_ON, cancel=False)
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_ON)
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
def test_verify_vm_state_revert_snapshot(provider, parent_vm, create_vm):
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
    power = create_vm.POWER_ON if parent_vm.startswith('on') else create_vm.POWER_OFF
    memory = 'with_memory' in parent_vm

    create_vm.power_control_from_cfme(option=power, cancel=False)
    create_vm.mgmt.wait_for_steady_state()
    setup_snapshot_env(create_vm, memory)
    assert bool(create_vm.mgmt.is_running) == memory


@pytest.mark.provider([VMwareProvider])
def test_operations_suspended_vm(create_vm, soft_assert):
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
    snapshot1 = new_snapshot(create_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active")
    # Suspend the VM
    create_vm.mgmt.ensure_state(VmState.SUSPENDED)
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_SUSPENDED)
    # Create second snapshot when VM is suspended
    snapshot2 = new_snapshot(create_vm)
    snapshot2.create()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh,
             message="Waiting for the second snapshot to become active")
    # Try to revert to first snapshot while the VM is suspended
    snapshot1.revert_to()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active after revert")
    # Check VM state, VM should be off
    assert create_vm.mgmt.is_stopped
    # Revert back to second snapshot
    snapshot2.revert_to()
    wait_for(lambda: snapshot2.active, num_sec=300, delay=20, fail_func=snapshot2.refresh,
             message="Waiting for the second snapshot to become active after revert")
    # Check VM state, VM should be suspended if VM version is 6.5
    # if version is 6.7 Vm state should be off (is_stopped)
    if create_vm.provider.version == 6.7:
        assert create_vm.mgmt.is_stopped
    else:
        assert create_vm.mgmt.is_suspended
    # Try to delete both snapshots while the VM is suspended
    # The delete method will make sure the snapshots are indeed deleted
    snapshot1.delete()
    snapshot2.delete()


@pytest.mark.provider([VMwareProvider])
def test_operations_powered_off_vm(create_vm):
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/2h
    """
    # Make sure the VM is off
    create_vm.power_control_from_cfme(option=create_vm.POWER_OFF, cancel=False)
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_OFF)
    # Create first snapshot
    snapshot1 = new_snapshot(create_vm)
    snapshot1.create()
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=snapshot1.refresh,
             message="Waiting for the first snapshot to become active")
    # Create second snapshot
    snapshot2 = new_snapshot(create_vm)
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


def test_snapshot_history_btn(create_vm, provider):
    """Tests snapshot history button
    Metadata:
        test_flag: snapshot

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
    """
    snapshot = new_snapshot(create_vm, has_name=(not provider.one_of(RHEVMProvider)))
    snapshot.create()
    vm_details_view = navigate_to(create_vm, 'Details')
    item = f'"Snapshots" for Virtual Machine "{create_vm.name}"'
    vm_details_view.toolbar.history.item_select(item)
    snapshot_view = create_vm.create_view(InfraVmSnapshotView)
    assert snapshot_view.is_displayed


@pytest.fixture
def add2snaps_del1(provider, create_vm):
    has_name = not provider.one_of(RHEVMProvider)
    snapshot1 = new_snapshot(create_vm, has_name=has_name)
    snapshot1.create()
    snapshot2 = new_snapshot(create_vm, has_name=has_name)
    snapshot2.create()
    snapshot1.delete()


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1395116])
def test_snapshot_link_after_delete(create_vm, add2snaps_del1):
    """Tests snapshot link and history button after delete
    Metadata:
        test_flag: snapshot
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
    snapshot_view = navigate_to(create_vm, 'SnapshotsAll')
    back_to_vm_item = f'VM and Instance "{create_vm.name}"'
    snapshot_view.toolbar.history.item_select(back_to_vm_item)
    vm_details_view = navigate_to(create_vm, 'Details')  # no nav should be needed.
    snapshot_item = f'"Snapshots" for Virtual Machine "{create_vm.name}"'
    vm_details_view.toolbar.history.item_select(snapshot_item)
    snapshot_view = create_vm.create_view(InfraVmSnapshotView)
    assert snapshot_view.is_displayed
    # Now go back to Details and click on the snapshots link
    vm_details_view = navigate_to(create_vm, 'Details')
    vm_details_view.entities.summary('Properties').click_at("Snapshots")
    assert snapshot_view.is_displayed


@pytest.mark.provider([VMwareProvider])
def test_create_snapshot_via_ae(appliance, request, domain, create_vm):
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
    snapshot = InfraVm.Snapshot(name=snap_name, parent_vm=create_vm)
    simulate(
        appliance=appliance,
        instance="Request",
        request="snapshot",
        target_type='VM and Instance',
        target_object=create_vm.name,
        execute_methods=True,
        attributes_values={"snap_name": snap_name})

    wait_for(lambda: snapshot.exists, timeout="2m", delay=10,
             fail_func=create_vm.provider.browser.refresh, handle_exception=True,
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
