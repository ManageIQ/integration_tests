import pytest
from utils import testgen
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_api_port(provider):
    port = provider.get_yaml_data()['port']
    assert provider.summary.properties.api_port.value == port,\
        'Invalid API Port'
