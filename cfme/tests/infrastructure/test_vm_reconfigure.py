import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.wait import wait_for
from cfme.utils.generators import random_vm_name


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider, RHEVMProvider],
                         required_fields=['templates'],
                         scope='module'),
]


@pytest.yield_fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = VM.factory(random_vm_name(context='reconfig'), provider, small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.cleanup_on_provider()


@pytest.fixture(scope='function')
def ensure_vm_stopped(small_vm):
    if small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_OFF):
        small_vm.power_control_from_provider(small_vm.POWER_OFF)
        small_vm.wait_for_vm_state_change(small_vm.STATE_OFF)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.fixture(scope='function')
def ensure_vm_running(small_vm):
    if small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_ON):
        small_vm.power_control_from_provider(small_vm.POWER_ON)
        small_vm.wait_for_vm_state_change(small_vm.STATE_ON)
    else:
        raise Exception("Unknown power state - unable to continue!")


@pytest.mark.rhv1
@pytest.mark.parametrize('change_type', ['cores_per_socket', 'sockets', 'memory'])
def test_vm_reconfig_add_remove_hw_cold(
        provider, small_vm, ensure_vm_stopped, change_type):

    orig_config = small_vm.configuration.copy()
    new_config = orig_config.copy()
    if change_type == 'cores_per_socket':
        new_config.hw.cores_per_socket = new_config.hw.cores_per_socket + 1
    elif change_type == 'sockets':
        new_config.hw.sockets = new_config.hw.sockets + 1
    elif change_type == 'memory':
        new_config.hw.mem_size = new_config.hw.mem_size_mb + 512
        new_config.hw.mem_size_unit = 'MB'

    reconfigure_request = small_vm.reconfigure(new_config)
    # VM reconfiguration verification
    wait_for(reconfigure_request.is_succeeded, timeout=360, delay=45,
             message="confirm that vm was reconfigured")
    wait_for(
        lambda: small_vm.configuration == new_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that {} was added".format(change_type))

    # Reverting changes back
    reconfigure_request = small_vm.reconfigure(orig_config)
    # VM reconfiguration verification
    wait_for(reconfigure_request.is_succeeded, timeout=360, delay=45,
             message="confirm that vm was reconfigured")
    wait_for(
        lambda: small_vm.configuration == orig_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that previously-added {} was removed".format(change_type))


@pytest.mark.rhv1
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
@pytest.mark.uncollectif(
    # Disk modes cannot be specified when adding disk to VM in RHV provider
    lambda disk_mode, provider: disk_mode != 'persistent' and provider.one_of(RHEVMProvider))
def test_vm_reconfig_add_remove_disk_cold(
        provider, small_vm, ensure_vm_stopped, disk_type, disk_mode):

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


def test_reconfig_vm_negative_cancel(provider, small_vm, ensure_vm_stopped):
    """ Cancel reconfiguration changes """
    config_vm = small_vm.configuration.copy()

    # Some changes in vm reconfigure before cancel
    config_vm.hw.cores_per_socket = config_vm.hw.cores_per_socket + 1
    config_vm.hw.sockets = config_vm.hw.sockets + 1
    config_vm.hw.mem_size = config_vm.hw.mem_size_mb + 512
    config_vm.hw.mem_size_unit = 'MB'
    config_vm.add_disk(
        size=5, size_unit='GB', type='thin', mode='persistent')

    small_vm.reconfigure(config_vm, cancel=True)
