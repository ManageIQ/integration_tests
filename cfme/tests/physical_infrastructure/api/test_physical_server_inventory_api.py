import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.rest import assert_response

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([LenovoProvider], scope='module')
]


@pytest.fixture(scope="module")
def physical_server(setup_provider_modscope, appliance):
    physical_server = appliance.rest_api.collections.physical_servers[0]
    return physical_server


def test_get_hardware(appliance, physical_server):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    physical_server.reload(attributes=['hardware'])
    assert_response(appliance)
    assert physical_server.hardware is not None


@pytest.mark.parametrize('attribute', ['firmwares', 'nics', 'ports'])
def test_get_hardware_attributes(appliance, physical_server, attribute):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    expanded_attribute = f'hardware.{attribute}'
    physical_server.reload(attributes=[expanded_attribute])
    assert_response(appliance)
    assert physical_server.hardware[attribute] is not None


def test_get_asset_detail(appliance, physical_server):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    physical_server.reload(attributes=['asset_detail'])
    assert_response(appliance)
    assert physical_server.asset_detail is not None
