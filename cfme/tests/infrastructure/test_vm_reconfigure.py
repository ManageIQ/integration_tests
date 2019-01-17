import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for
from cfme.utils.generators import random_vm_name

from wrapanapi import VmState


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
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
def small_vm(appliance, provider, small_template_modscope):
    """This fixture is function-scoped, because there is no un-ambiguous way how to search for
    reconfigure request in UI in situation when you have two requests for the same reconfiguration
    and for the same VM name. This happens if you run test_vm_reconfig_add_remove_hw_cold and then
    test_vm_reconfig_add_remove_hw_hot or vice versa. Making thix fixture function-scoped will
    ensure that the VM under test has a different name each time so the reconfigure requests
    are unique as a result."""
    vm = appliance.collections.infra_vms.instantiate(random_vm_name(context='reconfig'),
                                                     provider,
                                                     small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.cleanup_on_provider()


@pytest.fixture(scope='function')
def ensure_vm_stopped(small_vm):
    if small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_OFF):
        small_vm.mgmt.ensure_state(VmState.STOPPED)
        small_vm.wait_for_vm_state_change(small_vm.STATE_OFF)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.fixture(scope='function')
def ensure_vm_running(small_vm):
    if small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_ON):
        small_vm.mgmt.ensure_state(VmState.RUNNING)
        small_vm.wait_for_vm_state_change(small_vm.STATE_ON)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.mark.rhel_testing
@pytest.mark.rhv1
@pytest.mark.parametrize('change_type', ['cores_per_socket', 'sockets', 'memory'])
def test_vm_reconfig_add_remove_hw_cold(provider, small_vm, ensure_vm_stopped, change_type):
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
    """
    orig_config = small_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)

    # Apply new config
    reconfigure_vm(small_vm, new_config)

    # Revert back to original config
    reconfigure_vm(small_vm, orig_config)


@pytest.mark.rhel_testing
@pytest.mark.rhv1
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
@pytest.mark.uncollectif(
    # Disk modes cannot be specified when adding disk to VM in RHV provider
    lambda disk_mode, provider: disk_mode != 'persistent' and provider.one_of(RHEVMProvider))
def test_vm_reconfig_add_remove_disk_cold(
        provider, small_vm, ensure_vm_stopped, disk_type, disk_mode):

    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
    """
    orig_config = small_vm.configuration.copy()
    new_config = orig_config.copy()
    new_config.add_disk(
        size=500, size_unit='MB', type=disk_type, mode=disk_mode)

    add_disk_request = small_vm.reconfigure(new_config)
    # Add disk request verification
    wait_for(add_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that disk was added")
    # Add disk UI verification
    wait_for(
        lambda: small_vm.configuration.num_disks == new_config.num_disks, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that disk was added")
    msg = "Disk wasn't added to VM config"
    assert small_vm.configuration.num_disks == new_config.num_disks, msg

    remove_disk_request = small_vm.reconfigure(orig_config)
    # Remove disk request verification
    wait_for(remove_disk_request.is_succeeded, timeout=360, delay=45,
             message="confirm that previously-added disk was removed")
    # Remove disk UI verification
    wait_for(
        lambda: small_vm.configuration.num_disks == orig_config.num_disks, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that previously-added disk was removed")
    msg = "Disk wasn't removed from VM config"
    assert small_vm.configuration.num_disks == orig_config.num_disks, msg


@pytest.mark.rhv3
def test_reconfig_vm_negative_cancel(provider, small_vm, ensure_vm_stopped):
    """ Cancel reconfiguration changes

    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
    """
    config_vm = small_vm.configuration.copy()

    # Some changes in vm reconfigure before cancel
    config_vm.hw.cores_per_socket = config_vm.hw.cores_per_socket + 1
    config_vm.hw.sockets = config_vm.hw.sockets + 1
    config_vm.hw.mem_size = config_vm.hw.mem_size_mb + 512
    config_vm.hw.mem_size_unit = 'MB'
    config_vm.add_disk(
        size=5, size_unit='GB', type='thin', mode='persistent')

    small_vm.reconfigure(config_vm, cancel=True)


@pytest.mark.rhv1
@pytest.mark.uncollectif(lambda provider: provider.one_of(VMwareProvider))
@pytest.mark.parametrize('change_type', ['sockets', 'memory'])
@pytest.mark.meta(blockers=[BZ(1632782, forced_streams=['5.10'])])
def test_vm_reconfig_add_remove_hw_hot(provider, small_vm, ensure_vm_running, change_type):
    """Change number of CPU sockets and amount of memory while VM is runnng.
        Chaning number of cores per socket on running VM is not supported by RHV.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    orig_config = small_vm.configuration.copy()
    new_config = prepare_new_config(orig_config, change_type)

    # Apply new config
    reconfigure_vm(small_vm, new_config)

    # Revert back to original config
    reconfigure_vm(small_vm, orig_config)


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('change_type', ['sockets', 'memory'])
def test_vm_reconfig_add_remove_hw_hot_vmware():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.5
        casecomponent: infra
        testSteps:
            1. Change number of CPU sockets and amount of memory while VM is runnng.
            2. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm  
            3. Go to VM reconfiguration
            4.Change number of CPU sockets and amount of memory, save and submit
            5. Check the count in VM details page
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
def test_vm_reconfig_add_remove_disk_hot():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.5
        casecomponent: infra
        testSteps:
            1. Add and remove the disk while VM is running
            2. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm  
            3. Go to VM reconfiguration
            4. Click on Add Disk -> select disk_type and disk_mode , save and submit
            5. Check the count in VM details page
            6. Remove the disk and Check the count in VM details page
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
def test_vm_reconfig_resize_disk_cold():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.9
        casecomponent: infra
        testSteps:
            1. Resize the disk while VM is not running
            2. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm  
            3. Go to VM reconfiguration
            4. Click on Add Disk -> select disk_type and disk_mode , save and submit
            5. Go to VM reconfiguration and resize the disk 
            6. Check the changes in VM reconfiguration page
            7. Remove the disk
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
def test_vm_reconfig_resize_disk_hot():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.9
        casecomponent: infra
        testSteps:
            1. Resize the disk while VM is running
            2. Go to Compute -> infrastructure -> Virtual Machines -> Select Vm  
            3. Go to VM reconfiguration
            4. Click on Add Disk -> select disk_type and disk_mode , save and submit
            5. Go to VM reconfiguration and resize the disk 
            6. Check the changes in VM reconfiguration page
            7. Remove the disk
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize(
    'adapters_type', ['DPortGroup', 'VmNetwork', 'MgmtNetwork', 'VmKernel'])
def test_vm_reconfig_add_remove_network_adapters():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.9
        casecomponent: infra
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
def test_reconfigure_vm_vmware_mem_multiple():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: medium
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.6
        casecomponent: infra
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. provision 2 new vms
            3. power off 1 vm -> select both vms
            4. configure-->reconfigure vm
            5. power on vm
            6. check changes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_reconfig_attach_iso_vsphere67_nested():
    """
    
    Bugzillas:
        * 1533728

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: high
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.10
        casecomponent: infra
        testSteps:
            1. Add vmware provider
            2. provision 1 new vms
            3. Run a Smartstate analysis on the Datastore (to get the list of ISO files)
            4. configure-->reconfigure vm
            5. Select an ISO (This should allow you to select an ISO to attach to the CD drive)
            6. check changes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_vm_vmware_sockets_multiple():
    """ Test changing the cpu sockets of multiple vms at the same time.

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: medium
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.6
        casecomponent: infra
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
def test_reconfigure_vm_vmware_cores_multiple():
    """ Test changing the cpu cores of multiple vms at the same time.

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: medium
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.6
        casecomponent: infra
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
@pytest.mark.tier(3)
def test_reconfigure_add_disk_cold():
    """ Test adding 16th disk to test how a new scsi controller is handled.
    
    Bugzilla:
        * 1337310

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: low
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.7
        casecomponent: infra
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. provision a new vm with 15 disks
            3. Add a new disk with CloudForms using the VM Reconfigure dialog
            4. Check new SCSI controller in vm
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_add_disk_cold_controller_sas():
    """ 
    
    Bugzilla:
        * 1445874

    Polarion:
        assignee: nansari
        initialEstimate: 1/6h
        caseimportance: medium
        caselevel: integration
        caseposneg: positive
        caseautomation: Non Automated
        testtype: functional
        startsin: 5.5
        casecomponent: infra
        testSteps:
            1. get new configured appliance ->add vmware provider
            2. Add 15 disks to an existing VM with Controller type set to SAS
            3. look at the 16th Disk Controller Type
            4. Check controller type
            5. Should be SAS like exiting Controller
    """
    pass


