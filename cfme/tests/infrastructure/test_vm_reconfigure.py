import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.wait import wait_for
from cfme.utils.generators import random_vm_name

pytest_generate_tests = testgen.generate(
    [VMwareProvider, RHEVMProvider],
    required_fields=['templates'],
    scope="module")

pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.long_running,
    pytest.mark.tier(2)]


@pytest.yield_fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = VM.factory(random_vm_name(context='reconfig'), provider, small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.delete_from_provider()


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

    small_vm.reconfigure(new_config)
    wait_for(
        lambda: small_vm.configuration == new_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that {} was added".format(change_type))

    small_vm.reconfigure(orig_config)
    wait_for(
        lambda: small_vm.configuration == orig_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that previously-added {} was removed".format(change_type))


@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
@pytest.mark.parametrize(
    'disk_mode', ['persistent', 'independent_persistent', 'independent_nonpersistent'])
@pytest.mark.uncollectif(lambda provider: provider.one_of(RHEVMProvider))
def test_vm_reconfig_add_remove_disk_cold(
        provider, small_vm, ensure_vm_stopped, disk_type, disk_mode):

    orig_config = small_vm.configuration.copy()
    new_config = orig_config.copy()
    new_config.add_disk(
        size=5, size_unit='GB', type=disk_type, mode=disk_mode)

    small_vm.reconfigure(new_config)
    wait_for(
        lambda: small_vm.configuration == new_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that disk was added")

    small_vm.reconfigure(orig_config)
    wait_for(
        lambda: small_vm.configuration == orig_config, timeout=360, delay=45,
        fail_func=small_vm.refresh_relationships,
        message="confirm that previously-added disk was removed")
