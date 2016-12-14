import pytest
from utils import testgen
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_api_port(provider, soft_assert):
    soft_assert(provider.summary.properties.api_port.value.isdigit(),
                "Invalid API Port")
