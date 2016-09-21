from utils import testgen
import pytest


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_api_port(provider, soft_assert):
    soft_assert(provider.summary.properties.api_port.value.isdigit(),
                "Invalid API Port")
