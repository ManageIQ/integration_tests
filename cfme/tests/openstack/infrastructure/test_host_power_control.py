from __future__ import absolute_import
import pytest
from navmazing import NavigationDestinationNotFound

from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import Quadicon
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version

pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')

pytestmark = [pytest.mark.uncollectif(lambda: current_version() < '5.7'),
              pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope='module')
def host_on(provider):
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"

    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    my_host_on = Host(name=quad.name, provider=provider)

    if my_host_on.get_power_state() == 'off':
        my_host_on.power_on()
        my_host_on.wait_for_host_state_change('on', 1000)
    return my_host_on


@pytest.fixture(scope='module')
def host_off(provider):
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"

    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    my_host_off = Host(name=quad.name, provider=provider)

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
