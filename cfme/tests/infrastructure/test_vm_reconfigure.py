import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException
from wrapanapi import VmState

from cfme import test_requirements
from cfme.exceptions import RequestException
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.infrastructure.virtual_machines import InfraVmReconfigureView
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
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
def ensure_vm_stopped(create_vm):
    if create_vm.is_pwr_option_available_in_cfme(create_vm.POWER_OFF):
        create_vm.mgmt.ensure_state(VmState.STOPPED)
        create_vm.wait_for_vm_state_change(create_vm.STATE_OFF)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.fixture(scope='function')
def ensure_vm_running(create_vm):
    if create_vm.is_pwr_option_available_in_cfme(create_vm.POWER_ON):
        create_vm.mgmt.ensure_state(VmState.RUNNING)
        create_vm.wait_for_vm_state_change(create_vm.STATE_ON)
    else:
        raise Exception("Unknown power state - unable to continue!")


def _vm_state(vm, state):
    if state == "cold" and vm.is_pwr_option_available_in_cfme(vm.POWER_OFF):
        ensure_state = VmState.STOPPED
        state_change = vm.STATE_OFF
    elif state == "hot" and vm.is_pwr_option_available_in_cfme(vm.POWER_ON):
        ensure_state = VmState.RUNNING
        state_change = vm.STATE_ON
    else:
        raise ValueError("Unknown power state - unable to continue!")

    vm.mgmt.ensure_state(ensure_state)
    vm.wait_for_power_state_change_rest(state_change)


@pytest.fixture(params=["cold", "hot"])
def vm_state(request, create_vm):
    _vm_state(create_vm, request.param)
    return request.param


@pytest.fixture(scope='function')
def enable_hot_plugin(provider, create_vm, ensure_vm_stopped):
    # Operation on Provider side
    # Hot plugin enable only needs for Vsphere Provider
    if provider.one_of(VMwareProvider):
        vm = provider.mgmt.get_vm(create_vm.name)
        vm.cpu_hot_plug = True
        vm.memory_hot_plug = True


@pytest.fixture(params=["hot", "cold"])
def multiple_vm_state(request, config_type, create_vms_modscope):
    for vm in create_vms_modscope:
        if request.param == "hot":
            vm.mgmt.ensure_state(VmState.STOPPED)
            if config_type == "sockets":
                vm.mgmt.cpu_hot_plug = True
            else:
                vm.mgmt.memory_hot_plug = True
            vm.mgmt.ensure_state(VmState.RUNNING)
        _vm_state(vm, request.param)
    return request.param


@pytest.fixture
def request_succeeded(appliance):
    def _is_succeeded(reconfig_request):
        try:
            reconfig_request.wait_for_request()
            return reconfig_request.is_succeeded()
        except RequestException:
            view = navigate_to(reconfig_request.parent, "All")
            # Get the latest request
            request_id = max(
                int(row.request_id.text)
                for row in view.table.rows(description__contains=reconfig_request.description)
            )
            request_rest = appliance.rest_api.collections.requests.get(id=request_id)
            wait_for(
                lambda: request_rest.request_state == "finished",
                fail_func=request_rest.reload,
                timeout=120,
            )
            return request_rest.status == "Ok"
        return

    return _is_succeeded


@pytest.mark.parametrize('change_type', ['cores_per_socket', 'sockets', 'memory'])
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_reconfig_add_remove_hw_cold(provider, create_vm, ensure_vm_stopped, change_type):
    """
    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/3h
        tags: reconfigure
    """
    orig_config = create_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)

    # Apply new config
    reconfigure_vm(create_vm, new_config)

    # Revert back to original config
    reconfigure_vm(create_vm, orig_config)


@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
# Disk modes cannot be specified when adding disk to VM in RHV provider
@pytest.mark.uncollectif(lambda disk_mode, provider:
                         disk_mode != 'persistent' and provider.one_of(RHEVMProvider),
                         reason='Disk modes cannot be specified on RHEVM, only persistent included')
@pytest.mark.meta(
    blockers=[BZ(1692801, forced_streams=['5.10'],
                 unblock=lambda provider: not provider.one_of(RHEVMProvider))]
)
def test_vm_reconfig_add_remove_disk(provider, create_vm, vm_state, disk_type, disk_mode):
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
    orig_config = create_vm.configuration.copy()
    new_config = orig_config.copy()
    new_config.add_disk(
        size=500, size_unit='MB', type=disk_type, mode=disk_mode)

    add_disk_request = create_vm.reconfigure(new_config)
    # Add disk request verification
    wait_for(add_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that disk was added")
    # Add disk UI verification
    wait_for(
        lambda: create_vm.configuration.num_disks == new_config.num_disks, timeout=360, delay=45,
        fail_func=create_vm.refresh_relationships,
        message="confirm that disk was added")
    msg = "Disk wasn't added to VM config"
    assert create_vm.configuration.num_disks == new_config.num_disks, msg

    remove_disk_request = create_vm.reconfigure(orig_config)
    # Remove disk request verification
    wait_for(remove_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that previously-added disk was removed")
    # Remove disk UI verification
    wait_for(
        lambda: create_vm.configuration.num_disks == orig_config.num_disks, timeout=360, delay=45,
        fail_func=create_vm.refresh_relationships,
        message="confirm that previously-added disk was removed")
    msg = "Disk wasn't removed from VM config"
    assert create_vm.configuration.num_disks == orig_config.num_disks, msg


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_reconfig_vm_negative_cancel(provider, create_vm, ensure_vm_stopped):
    """ Cancel reconfiguration changes

    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/3h
        tags: reconfigure
    """
    config_vm = create_vm.configuration.copy()

    # Some changes in vm reconfigure before cancel
    config_vm.hw.cores_per_socket = config_vm.hw.cores_per_socket + 1
    config_vm.hw.sockets = config_vm.hw.sockets + 1
    config_vm.hw.mem_size = config_vm.hw.mem_size_mb + 512
    config_vm.hw.mem_size_unit = 'MB'
    config_vm.add_disk(
        size=5, size_unit='GB', type='thin', mode='persistent')

    create_vm.reconfigure(config_vm, cancel=True)


@pytest.mark.meta(
    blockers=[BZ(1697967, unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.parametrize('change_type', ['sockets', 'memory'])
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_reconfig_add_remove_hw_hot(
        provider, create_vm, enable_hot_plugin, ensure_vm_running, change_type):
    """Change number of CPU sockets and amount of memory while VM is running.
    Changing number of cores per socket on running VM is not supported by RHV.

    Polarion:
        assignee: nansari
        casecomponent: Infra
        initialEstimate: 1/4h
        tags: reconfigure
    """
    orig_config = create_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)
    assert vars(orig_config.hw) != vars(new_config.hw)

    # Apply new config
    reconfigure_vm(create_vm, new_config)

    assert vars(create_vm.configuration.hw) == vars(new_config.hw)

    # Revert back to original config only supported by RHV
    if provider.one_of(RHEVMProvider):
        reconfigure_vm(create_vm, orig_config)


@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize('disk_mode', ['persistent',
                                       'independent_persistent',
                                       'independent_nonpersistent'])
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
@pytest.mark.uncollectif(lambda disk_mode, vm_state:
                         disk_mode == 'independent_nonpersistent' and vm_state == 'hot',
                         reason='Disk resize not supported for hot vm independent_nonpersistent')
def test_vm_reconfig_resize_disk(appliance, create_vm, vm_state, disk_type, disk_mode):
    """ Resize the disk while VM is running and not running
     Polarion:
         assignee: nansari
         initialEstimate: 1/6h
         testtype: functional
         startsin: 5.9
         casecomponent: Infra
     """
    # get initial disks for later comparison
    initial_disks = [disk.filename for disk in create_vm.configuration.disks]
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
    vm_reconfig_via_rest(appliance, "disk_add", create_vm.rest_api_entity.id, add_data)

    # assert the new disk was added
    assert wait_for(
        lambda: create_vm.configuration.num_disks > len(initial_disks),
        fail_func=create_vm.refresh_relationships,
        delay=5,
        timeout=200,
    )

    # there will always be 2 disks after the disk has been added
    disks_present = [disk.filename for disk in create_vm.configuration.disks]
    # get the newly added disk
    try:
        disk_added = list(set(disks_present) - set(initial_disks))[0]
    except IndexError:
        pytest.fail('Added disk not found in diff between initial and present disks')

    # resize the disk
    disk_size = 500
    new_config = create_vm.configuration.copy()
    new_config.resize_disk(size_unit='MB', size=disk_size, filename=disk_added)
    resize_disk_request = create_vm.reconfigure(new_configuration=new_config)

    # Resize disk request verification
    wait_for(resize_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that disk was Resize")

    # assert the new disk size was added
    view = navigate_to(create_vm, 'Reconfigure')
    assert int(view.disks_table.row(name=disk_added)["Size"].text) == disk_size


@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1631448, 1696841])
@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize('disk_mode', ['persistent',
                                       'independent_persistent',
                                       'independent_nonpersistent'])
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_reconfig_resize_disk_snapshot(request, disk_type, disk_mode, create_vm, memory=False):
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
        parent_vm=create_vm
    )
    snapshot.create()
    request.addfinalizer(snapshot.delete)

    view = navigate_to(create_vm, 'Reconfigure')
    row = next(r for r in view.disks_table.rows())

    # Delete button should enabled
    assert row.actions.widget.is_enabled

    # Re-sized button should not displayed
    assert not row[9].widget.is_displayed


@pytest.mark.tier(1)
@pytest.mark.provider([VMwareProvider])
@pytest.mark.parametrize(
    "adapters_type",
    ["DPortGroup", "VM Network", "Management Network", "VMkernel"],
    ids=["DPortGroup", "VmNetwork", "MgmtNetwork", "VmKernel"],
)
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_reconfig_add_remove_network_adapters(request, adapters_type, create_vm):
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
    orig_config = create_vm.configuration.copy()

    # Create new configuration with new network adapter
    new_config = orig_config.copy()
    new_config.add_network_adapter(
        f"Network adapter {orig_config.num_network_adapters + 1}", vlan=adapters_type
    )
    add_adapter_request = create_vm.reconfigure(new_config)
    add_adapter_request.wait_for_request(method="ui")
    request.addfinalizer(add_adapter_request.remove_request)

    # Verify network adapter added or not
    wait_for(
        lambda: create_vm.configuration.num_network_adapters == new_config.num_network_adapters,
        timeout=120,
        delay=10,
        fail_func=create_vm.refresh_relationships,
        message="confirm that network adapter was added",
    )

    # Remove network adapter
    remove_adapter_request = create_vm.reconfigure(orig_config)
    remove_adapter_request.wait_for_request(method="ui")
    request.addfinalizer(remove_adapter_request.remove_request)

    # Verify network adapter removed or not
    wait_for(
        lambda: create_vm.configuration.num_network_adapters == orig_config.num_network_adapters,
        timeout=120,
        delay=10,
        fail_func=create_vm.refresh_relationships,
        message="confirm that network adapter was added",
    )


@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module")
@pytest.mark.parametrize("config_type", ["sockets", "memory"])
@pytest.mark.parametrize("increase", [True, False], ids=["increase", "decrease"])
@pytest.mark.parametrize(
    "create_vms_modscope",
    [{"template_type": "full_template", "num_vms": 2}],
    ids=["full_template"],
    indirect=True,
)
def test_reconfigure_vm_vmware_multiple(
    appliance,
    config_type,
    create_vms_modscope,
    multiple_vm_state,
    increase,
    request,
    request_succeeded,
):
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
        expectedResults:
            1. Action should succeed
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
    """
    vms = create_vms_modscope
    all_view = navigate_to(vms[0], "AllForProvider")
    entities = [all_view.entities.get_entity(surf_pages=True, name=vm.name) for vm in vms]
    [entity.ensure_checked() for entity in entities]
    all_view.toolbar.configuration.item_select("Reconfigure Selected items")

    reconfig_view = vms[0].create_view(InfraVmReconfigureView, wait="20s")
    if config_type == "memory":
        reconfig_view.memory.fill(True)
        reconfig_view.mem_size_unit.select_by_visible_text("GB")
        current_memory = int(reconfig_view.mem_size.value)
        if increase:
            new_memory = current_memory + 1
        else:
            if current_memory < 1:
                pytest.skip("Cannot decrease memory below 1.")
            new_memory = current_memory - 1
        reconfig_view.mem_size.fill(new_memory)
        request_description = f"VM Reconfigure for: Multiple VMs - Memory: {new_memory * 1024} MB"
    else:
        reconfig_view.cpu.fill(True)
        current_processors = int(reconfig_view.sockets.selected_option)
        if increase:
            new_processor = current_processors + 1
        else:
            if current_processors < 1:
                pytest.skip("Cannot decrease sockets number below 1.")
            new_processor = current_processors - 1
        reconfig_view.sockets.select_by_visible_text(str(new_processor))
        request_description = (
            f"VM Reconfigure for: Multiple VMs - Processor Sockets: {new_processor}"
        )

    reconfig_view.submit_button.click()
    reconfig_request = appliance.collections.requests.instantiate(
        description=request_description, partial_check=True
    )

    @request.addfinalizer
    def _finalize():
        try:
            reconfig_request.remove_request()
        except (RequestException, NoSuchElementException):
            # sometimes the delete button is not present on the page.
            pass

    if multiple_vm_state == "hot" and not increase:
        assert not request_succeeded(reconfig_request)
    else:
        assert request_succeeded(reconfig_request)


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
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_disk_reconfig_via_rest(appliance, create_vm):
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
    vm_id = appliance.rest_api.collections.vms.get(name=create_vm.name).id
    # get initial disks for later comparison
    initial_disks = [disk.filename for disk in create_vm.configuration.disks]

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
        lambda: create_vm.configuration.num_disks > len(initial_disks),
        fail_func=create_vm.refresh_relationships,
        delay=5,
        timeout=200,
    )

    # Disk GUID is displayed instead of disk name in the disks table for a rhev VM, and passing
    # disk GUID to the delete method results in failure, so skip this part until the BZ is fixed.
    if not (BZ(1691635).blocks and create_vm.provider.one_of(RHEVMProvider)):

        # there will always be 2 disks after the disk has been added
        disks_present = [disk.filename for disk in create_vm.configuration.disks]
        disk_added = list(set(disks_present) - set(initial_disks))[0]

        # remove the newly added disk from VM
        delete_data = [{"disk_name": disk_added, "delete_backing": False}]
        vm_reconfig_via_rest(appliance, "disk_remove", vm_id, delete_data)

        # assert the disk was removed
        try:
            wait_for(
                lambda: create_vm.configuration.num_disks == len(initial_disks),
                fail_func=create_vm.refresh_relationships,
                delay=5,
                timeout=200,
            )
        except TimedOutError:
            assert (
                False
            ), "Number of disks expected was {expected}, found {actual}".format(
                expected=len(initial_disks), actual=create_vm.configuration.num_disks
            )


@pytest.mark.manual
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([VMwareProvider, RHEVMProvider],
                      required_fields=['templates'], selector=ONE_PER_TYPE)
@test_requirements.multi_region
def test_vm_reconfigure_from_global_region(context):
    """
    reconfigure a VM via CA

    Polarion:
        assignee: tpapaioa
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
