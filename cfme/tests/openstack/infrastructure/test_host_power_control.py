import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider

pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
@pytest.yield_fixture(scope='function')
def host(provider):
    if provider.load_all_provider_nodes():
        my_quads = list(Quadicon.all())
        quad = my_quads[0]
        my_host = Host(name=quad.name)
        if my_host.get_power_state() == 'off':
            my_host.wait_for_host_state_change('on', 1000)
        yield my_host


def test_host_power_off(host):
    host.power_off()
    host.refresh()
    result = host.wait_for_host_state_change('off', timeout=1000)
    assert result


def test_host_power_on(provider):
    nodes_bool = provider.load_all_provider_nodes()
    if not nodes_bool:
        assert "Missing nodes in provider's details"
    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    host = Host(name=quad.name)
    if host.get_power_state() == 'off':
        host.power_on()
        host.refresh()
    else:
        pytest.fail("Power State is unknown")

    result = host.wait_for_host_state_change('on', timeout=600)
    assert result
