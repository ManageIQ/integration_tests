import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from utils import testgen
from utils.wait import wait_for
from utils.generators import random_vm_name

pytest_generate_tests = testgen.generate(
    [VMwareProvider, RHEVMProvider, SCVMMProvider],
    required_fields=['small_template'],
    scope="module")

pytestmark = [pytest.mark.usefixtures('setup_provider')]


@pytest.yield_fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = VM.factory(random_vm_name(context='reconfig'), provider)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.delete_from_provider()


@pytest.fixture(scope='function')
def ensure_power_state(small_vm, power_type):
    if power_type == 'cold' and small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_OFF):
        small_vm.power_control_from_provider(small_vm.POWER_OFF)
        small_vm.wait_for_vm_state_change(small_vm.STATE_OFF)
    elif small_vm.is_pwr_option_available_in_cfme(small_vm.POWER_ON):
        small_vm.power_control_from_provider(small_vm.POWER_ON)
        small_vm.wait_for_vm_state_change(small_vm.STATE_ON)


@pytest.mark.parametrize('power_type', ['hot', 'cold'])
@pytest.mark.parametrize('change_type', ['cores_per_socket', 'sockets', 'memory'])
def test_vm_reconfigure_add_remove_hw(
        provider, small_vm, ensure_power_state, power_type, change_type):

    orig_config = small_vm.get_configuration()

    new_config = orig_config.copy()
    if change_type in ('cores_per_socket', 'sockets'):
        updates = {change_type: new_config.hw[change_type] + 1}
    elif change_type == 'memory':
        updates = {'mem_size': new_config.hw['mem_size'] + 512}
    new_config.update_hw(**updates)

    # Add hardware
    small_vm.reconfigure(new_config)
    wait_for(lambda: small_vm.get_configuration() == new_config, timeout=360, delay=45)

    # Remove hardware
    small_vm.reconfigure(orig_config)
    wait_for(lambda: small_vm.get_configuration() == orig_config, timeout=360, delay=45)


@pytest.mark.parametrize('power_type', ['hot', 'cold'])
@pytest.mark.parametrize('disk_type', ['thin', 'thick'])
# Mode and Depeendent are put together because we don't want nonpersistent-independent combo
@pytest.mark.parametrize(
    'disk_mode_dependent',
    [['persistent', True], ['persistent', False], ['nonpersistent', True]],
    ids=['persistent-dependent', 'persistent-independent', 'nonpersistent-dependent'])
@pytest.mark.uncollectif(lambda provider: provider.one_of(RHEVMProvider))
def test_vm_reconfigure_add_remove_disk(
        provider, small_vm, ensure_power_state, power_type, disk_type, disk_mode_dependent):
    disk_mode, disk_dependent = disk_mode_dependent

    orig_config = small_vm.get_configuration()

    new_config = orig_config.copy()
    new_config.add_disk(
        size=5, size_unit='GB', type_=disk_type, mode=disk_mode, dependent=disk_dependent)

    # Add disk
    small_vm.reconfigure(new_config)
    wait_for(lambda: small_vm.get_configuration() == new_config, timeout=360, delay=45)

    # Remove disk
    small_vm.reconfigure(orig_config)
    wait_for(lambda: small_vm.get_configuration() == orig_config, timeout=360, delay=45)
