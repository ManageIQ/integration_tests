import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.rest import assert_response
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.reconfigure,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider, RHEVMProvider],
                         required_fields=['templates'],
                         scope='module'),
]


def prepare_new_config(orig_config, change_type):
    """Prepare configuration object for test case based on change_type."""
    new_config = orig_config.copy()
    if change_type == 'cores_per_socket':
        new_config.hw.cores_per_socket = new_config.hw.cores_per_socket + 1
    elif change_type == 'sockets':
        new_config.hw.sockets = new_config.hw.sockets + 1
    elif change_type == 'memory':
        new_config.hw.mem_size = new_config.hw.mem_size_mb + 512
        new_config.hw.mem_size_unit = 'MB'

    return new_config


def reconfigure_vm(vm, config):
    """Reconfigure VM to have the supplies config."""
    reconfigure_request = vm.reconfigure(config)
    wait_for(reconfigure_request.is_succeeded, timeout=360, delay=45,
        message="confirm that vm was reconfigured")
    wait_for(
        lambda: vm.configuration == config, timeout=360, delay=45,
        fail_func=vm.refresh_relationships,
        message="confirm that config was applied. Hardware: {}, disks: {}"
                .format(vars(config.hw), config.disks))


@pytest.fixture(scope='function')
def full_vm(appliance, provider, full_template):
    """This fixture is function-scoped, because there is no un-ambiguous way how to search for
    reconfigure request in UI in situation when you have two requests for the same reconfiguration
    and for the same VM name. This happens if you run test_vm_reconfig_add_remove_hw_cold and then
    test_vm_reconfig_add_remove_hw_hot or vice versa. Making thix fixture function-scoped will
    ensure that the VM under test has a different name each time so the reconfigure requests
    are unique as a result."""
    vm = appliance.collections.infra_vms.instantiate(random_vm_name(context='reconfig'),
                                                     provider,
                                                     full_template.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.cleanup_on_provider()


@pytest.fixture(scope='function')
def ensure_vm_stopped(full_vm):
    if full_vm.is_pwr_option_available_in_cfme(full_vm.POWER_OFF):
        full_vm.mgmt.ensure_state(VmState.STOPPED)
        full_vm.wait_for_vm_state_change(full_vm.STATE_OFF)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.fixture(scope='function')
def ensure_vm_running(full_vm):
    if full_vm.is_pwr_option_available_in_cfme(full_vm.POWER_ON):
        full_vm.mgmt.ensure_state(VmState.RUNNING)
        full_vm.wait_for_vm_state_change(full_vm.STATE_ON)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.fixture(params=["cold", "hot"])
def vm_state(request, full_vm):
    if request.param == "cold":
        if full_vm.is_pwr_option_available_in_cfme(full_vm.POWER_OFF):
            full_vm.mgmt.ensure_state(VmState.STOPPED)
            full_vm.wait_for_vm_state_change(full_vm.STATE_OFF)
        else:
            raise Exception("Unknown power state - unable to continue!")
    else:
        if full_vm.is_pwr_option_available_in_cfme(full_vm.POWER_ON):
            full_vm.mgmt.ensure_state(VmState.RUNNING)
            full_vm.wait_for_vm_state_change(full_vm.STATE_ON)
        else:
            raise Exception("Unknown power state - unable to continue!")

    yield request.param


@pytest.fixture(scope='function')
def enable_hot_plugin(provider, full_vm, ensure_vm_stopped):
    # Operation on Provider side
    # Hot plugin enable only needs for Vsphere Provider
    if provider.one_of(VMwareProvider):
        vm = provider.mgmt.get_vm(full_vm.name)
        vm.cpu_hot_plug = True
        vm.memory_hot_plug = True


@pytest.mark.rhv1
@pytest.mark.parametrize('change_type', ['cores_per_socket', 'sockets', 'memory'])
def test_vm_reconfig_add_remove_hw_cold(provider, full_vm, ensure_vm_stopped, change_type):
    """
    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/3h
        tags: reconfigure
    """
    orig_config = full_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)

    # Apply new config
    reconfigure_vm(full_vm, new_config)

    # Revert back to original config
    reconfigure_vm(full_vm, orig_config)


@pytest.mark.rhv1
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
# Disk modes cannot be specified when adding disk to VM in RHV provider
@pytest.mark.uncollectif(lambda disk_mode, provider:
                         disk_mode != 'persistent' and provider.one_of(RHEVMProvider),
                         reason='Disk modes cannot be specified on RHEVM, only persistent included')
@pytest.mark.meta(
    blockers=[BZ(1692801, forced_streams=['5.10'],
                 unblock=lambda provider: not provider.one_of(RHEVMProvider))]
)
def test_vm_reconfig_add_remove_disk(provider, full_vm, vm_state, disk_type, disk_mode):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.9
        casecomponent: Infra
        tags: reconfigure
        testSteps:
            1. Add and remove the disk while VM is stopped and running
            2. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm
            3. Go to VM reconfiguration
            4. Click on Add Disk -> select disk_type and disk_mode , save and submit
            5. Check the count in VM details page
            6. Remove the disk and Check the count in VM details page
    """
    orig_config = full_vm.configuration.copy()
    new_config = orig_config.copy()
    new_config.add_disk(
        size=500, size_unit='MB', type=disk_type, mode=disk_mode)

    add_disk_request = full_vm.reconfigure(new_config)
    # Add disk request verification
    wait_for(add_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that disk was added")
    # Add disk UI verification
    wait_for(
        lambda: full_vm.configuration.num_disks == new_config.num_disks, timeout=360, delay=45,
        fail_func=full_vm.refresh_relationships,
        message="confirm that disk was added")
    msg = "Disk wasn't added to VM config"
    assert full_vm.configuration.num_disks == new_config.num_disks, msg

    remove_disk_request = full_vm.reconfigure(orig_config)
    # Remove disk request verification
    wait_for(remove_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that previously-added disk was removed")
    # Remove disk UI verification
    wait_for(
        lambda: full_vm.configuration.num_disks == orig_config.num_disks, timeout=360, delay=45,
        fail_func=full_vm.refresh_relationships,
        message="confirm that previously-added disk was removed")
    msg = "Disk wasn't removed from VM config"
    assert full_vm.configuration.num_disks == orig_config.num_disks, msg


@pytest.mark.rhv3
def test_reconfig_vm_negative_cancel(provider, full_vm, ensure_vm_stopped):
    """ Cancel reconfiguration changes

    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/3h
        tags: reconfigure
    """
    config_vm = full_vm.configuration.copy()

    # Some changes in vm reconfigure before cancel
    config_vm.hw.cores_per_socket = config_vm.hw.cores_per_socket + 1
    config_vm.hw.sockets = config_vm.hw.sockets + 1
    config_vm.hw.mem_size = config_vm.hw.mem_size_mb + 512
    config_vm.hw.mem_size_unit = 'MB'
    config_vm.add_disk(
        size=5, size_unit='GB', type='thin', mode='persistent')

    full_vm.reconfigure(config_vm, cancel=True)


@pytest.mark.rhv1
@pytest.mark.meta(
    blockers=[BZ(1697967, unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.parametrize('change_type', ['sockets', 'memory'])
def test_vm_reconfig_add_remove_hw_hot(
        provider, full_vm, enable_hot_plugin, ensure_vm_running, change_type):
    """Change number of CPU sockets and amount of memory while VM is runnng.
    Changing number of cores per socket on running VM is not supported by RHV.

    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/4h
        tags: reconfigure
    """
    orig_config = full_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)
    assert vars(orig_config.hw) != vars(new_config.hw)

    # Apply new config
    reconfigure_vm(full_vm, new_config)

    assert vars(full_vm.configuration.hw) == vars(new_config.hw)

    # Revert back to original config only supported by RHV
    if provider.one_of(RHEVMProvider):
        reconfigure_vm(full_vm, orig_config)


@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize('disk_mode', ['persistent',
                                       'independent_persistent',
                                       'independent_nonpersistent'])
@pytest.mark.uncollectif(lambda disk_mode, vm_state:
                         disk_mode == 'independent_nonpersistent' and vm_state == 'hot',
                         reason='Disk resize not supported for hot vm independent_nonpersistent')
def test_vm_reconfig_resize_disk(appliance, full_vm, vm_state, disk_type, disk_mode):
    """ Resize the disk while VM is running and not running
     Polarion:
         assignee: nansari
         initialEstimate: 1/6h
         testtype: functional
         startsin: 5.9
         casecomponent: Infra
     """
    # get initial disks for later comparison
    initial_disks = [disk.filename for disk in full_vm.configuration.disks]
    add_data = [
        {
            "disk_size_in_mb": 20,
            "sync": True,
            "persistent": disk_mode != "independent_nonpersistent",
            "thin_provisioned": disk_type == "thin",
            "dependent": not "independent"in disk_mode,
            "bootable": False,
        }
    ]
    # disk will be added to the VM via REST
    vm_reconfig_via_rest(appliance, "disk_add", full_vm.rest_api_entity.id, add_data)

    # assert the new disk was added
    assert wait_for(
        lambda: full_vm.configuration.num_disks > len(initial_disks),
        fail_func=full_vm.refresh_relationships,
        delay=5,
        timeout=200,
    )

    # there will always be 2 disks after the disk has been added
    disks_present = [disk.filename for disk in full_vm.configuration.disks]
    # get the newly added disk
    try:
        disk_added = list(set(disks_present) - set(initial_disks))[0]
    except IndexError:
        pytest.fail('Added disk not found in diff between initial and present disks')

    # resize the disk
    disk_size = 500
    new_config = full_vm.configuration.copy()
    new_config.resize_disk(size_unit='MB', size=disk_size, filename=disk_added)
    resize_disk_request = full_vm.reconfigure(new_configuration=new_config)

    # Resize disk request verification
    wait_for(resize_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that disk was Resize")

    # assert the new disk size was added
    view = navigate_to(full_vm, 'Reconfigure')
    assert int(view.disks_table.row(name=disk_added)["Size"].text) == disk_size


@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1631448, 1696841])
@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize('disk_mode', ['persistent',
                                       'independent_persistent',
                                       'independent_nonpersistent'])
def test_vm_reconfig_resize_disk_snapshot(request, disk_type, disk_mode, full_vm, memory=False):
    """

    Bugzilla:
        1631448

    Polarion:
        assignee: nansari
        initialEstimate: 1/8h
        startsin: 5.11
        casecomponent: Infra
        caseposneg: negative
        setup:
            1. Have a VM running on vsphere provider
        testSteps:
            1. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm
            2. Create a snapshot for selected VM
            3. Go to VM reconfiguration and try to resize disk of the VM
        expectedResults:
            1. VM selected
            2. Snapshot created
            3. Resize is not allowed when snapshots are attached
    """

    snapshot = InfraVm.Snapshot(
        name=fauxfactory.gen_alphanumeric(start="snap_"),
        description=fauxfactory.gen_alphanumeric(start="desc_"),
        memory=memory,
        parent_vm=full_vm
    )
    snapshot.create()
    request.addfinalizer(snapshot.delete)

    view = navigate_to(full_vm, 'Reconfigure')
    row = next(r for r in view.disks_table.rows())

    # Delete button should enabled
    assert row.actions.widget.is_enabled

    # Re-sized button should not displayed
    assert not row[9].widget.is_displayed


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize(
    'adapters_type', ['DPortGroup', 'VmNetwork', 'MgmtNetwork', 'VmKernel'])
def test_vm_reconfig_add_remove_network_adapters(adapters_type):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.9
        casecomponent: Infra
        tags: reconfigure
        testSteps:
            1. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm
            2. Go to VM reconfiguration
            3. Click on Add Adapters -> select type , save and submit
            4. Check the changes in VM reconfiguration page
            5. Remove the Adapters
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.provider([VMwareProvider])
def test_reconfigure_vm_vmware_mem_multiple():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.6
        casecomponent: Infra
        tags: reconfigure
        setup:
            1. get new configured appliance ->add vmware provider
            2. provision 2 new vms
        testSteps:
            1. Hot increase
            2. Hot Decrease
            3. Cold Increase
            4. Cold Decrease
            5. Hot + Cold Increase
            6. Hot + Cold Decrease
        expectedResults:
            1. Action should succeed
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
            5. Action should succeed
            6. Action should Error
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.provider([VMwareProvider])
def test_reconfigure_vm_vmware_sockets_multiple():
    """ Test changing the cpu sockets of multiple vms at the same time.

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.6
        casecomponent: Infra
        tags: reconfigure
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. provision 2 new vms
            3. power off 1 vm -> select both vms
            4. configure-->reconfigure vm
            5. increase/decrease counts
            6. power on vm
            7. check changes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.provider([VMwareProvider])
def test_reconfigure_vm_vmware_cores_multiple():
    """ Test changing the cpu cores of multiple vms at the same time.

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.6
        casecomponent: Infra
        tags: reconfigure
        setup:
            1. get new configured appliance ->add vmware provider
            2. provision 2 new vms
        testSteps:
            1. Hot increase
            2. Hot Decrease
            3. Cold Increase
            4. Cold Decrease
            5. Hot + Cold Increase
            6. Hot + Cold Decrease
        expectedResults:
            1. Action should fail
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
            5. Action should fail
            6. Action should Error
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
@pytest.mark.provider([VMwareProvider])
def test_reconfigure_add_disk_cold():
    """ Test adding 16th disk to test how a new scsi controller is handled.

    Bugzilla:
        1337310

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.7
        casecomponent: Infra
        tags: reconfigure
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. provision a new vm with 15 disks
            3. Add a new disk with CloudForms using the VM Reconfigure dialog
            4. Check new SCSI controller in vm
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.provider([VMwareProvider])
def test_reconfigure_add_disk_cold_controller_sas():
    """

    Bugzilla:
        1445874

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.5
        casecomponent: Infra
        tags: reconfigure
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. Add 15 disks to an existing VM with Controller type set to SAS
            3. look at the 16th Disk Controller Type
            4. Check controller type
            5. Should be SAS like exiting Controller
    """
    pass


def vm_reconfig_via_rest(appliance, config_type, vm_id, config_data):
    payload = {
        "action": "create",
        "options": {
            "src_ids": [vm_id],
            "request_type": "vm_reconfigure",
            config_type: config_data,
        },
        "auto_approve": False,
    }
    appliance.rest_api.collections.requests.action.create(**payload)
    assert_response(appliance)
    return


@test_requirements.rest
@pytest.mark.tier(3)
def test_vm_disk_reconfig_via_rest(appliance, full_vm):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/10h
        setup:
            1. Add an infrastructure provider. Test for vcenter and rhv provider.
            2. Provision a VM.
        testSteps:
            1. Add a disk to the VM.
            2. Remove the disk from VM
        expectedResults:
            1. The disk must be added successfully.
            2. The disk must be removed successfully.
    Bugzilla:
        1618517
        1666593
        1620161
        1691635
        1692801
    """
    vm_id = appliance.rest_api.collections.vms.get(name=full_vm.name).id
    # get initial disks for later comparison
    initial_disks = [disk.filename for disk in full_vm.configuration.disks]

    # add a disk to VM
    add_data = [
        {
            "disk_size_in_mb": 20,
            "sync": True,
            "persistent": True,
            "thin_provisioned": False,
            "dependent": True,
            "bootable": False,
        }
    ]
    vm_reconfig_via_rest(appliance, "disk_add", vm_id, add_data)

    # assert the new disk was added
    assert wait_for(
        lambda: full_vm.configuration.num_disks > len(initial_disks),
        fail_func=full_vm.refresh_relationships,
        delay=5,
        timeout=200,
    )

    # Disk GUID is displayed instead of disk name in the disks table for a rhev VM, and passing
    # disk GUID to the delete method results in failure, so skip this part until the BZ is fixed.
    if not (BZ(1691635).blocks and full_vm.provider.one_of(RHEVMProvider)):

        # there will always be 2 disks after the disk has been added
        disks_present = [disk.filename for disk in full_vm.configuration.disks]
        disk_added = list(set(disks_present) - set(initial_disks))[0]

        # remove the newly added disk from VM
        delete_data = [{"disk_name": disk_added, "delete_backing": False}]
        vm_reconfig_via_rest(appliance, "disk_remove", vm_id, delete_data)

        # assert the disk was removed
        try:
            wait_for(
                lambda: full_vm.configuration.num_disks == len(initial_disks),
                fail_func=full_vm.refresh_relationships,
                delay=5,
                timeout=200,
            )
        except TimedOutError:
            assert (
                False
            ), "Number of disks expected was {expected}, found {actual}".format(
                expected=len(initial_disks), actual=full_vm.configuration.num_disks
            )


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([VMwareProvider, RHEVMProvider],
                      required_fields=['templates'], selector=ONE_PER_TYPE)
@test_requirements.multi_region
@test_requirements.reconfigure
def test_vm_reconfigure_from_global_region(context):
    """
    reconfigure a VM via CA

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        casecomponent: Infra
        initialEstimate: 1/3h
        testSteps:
            1. Have a VM created in the provider in the Remote region which is
               subscribed to Global.
            2. Reconfigure the VM using the Global appliance.
        expectedResults:
            1.
            2.
            3. VM reconfigured, no errors.
    """
    pass
