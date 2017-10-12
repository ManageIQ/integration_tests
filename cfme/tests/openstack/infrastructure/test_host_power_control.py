import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils import testgen
from cfme.utils.version import current_version

pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')

pytestmark = [pytest.mark.uncollectif(lambda: current_version() < '5.7'),
              pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope="module")
def host_collection(appliance):
    return appliance.collections.hosts


@pytest.fixture(scope='module')
def host_on(host_collection, provider):
    try:
        my_host_on = host_collection.all(provider)[0]
    except IndexError:
        assert False, "Missing nodes in provider's details"

    if my_host_on.get_power_state() == 'off':
        my_host_on.power_on()
        my_host_on.wait_for_host_state_change('on', 1000)
    return my_host_on


@pytest.fixture(scope='module')
def host_off(host_collection, provider):
    try:
        my_host_off = host_collection.all(provider)[0]
    except IndexError:
        assert False, "Missing nodes in provider's details"

    if my_host_off.get_power_state() == 'on':
        my_host_off.power_off()
        my_host_off.wait_for_host_state_change('off', 1000)
    return my_host_off


def test_host_power_off(host_on):
    host_on.power_off()
    host_on.refresh()
    result = host_on.wait_for_host_state_change('off', 1000)
    assert result


def test_host_power_on(host_off):
    host_off.power_on()
    host_off.refresh()
    result = host_off.wait_for_host_state_change('on', 1000)
    assert result
