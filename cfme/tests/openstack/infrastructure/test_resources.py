import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils import testgen


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate'),
              pytest.mark.usefixtures("setup_provider_modscope")]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')


def test_number_of_cpu(provider, soft_assert):
    navigate_to(provider, 'Details')
    v = provider.get_detail('Properties', 'Aggregate Node CPU Resources')
    soft_assert(float(v.split()[0]) > 0, "Aggregate Node CPU Resources is 0")
    v = provider.get_detail('Properties', 'Aggregate Node CPUs')
    soft_assert(int(v) > 0, "Aggregate Node CPUs is 0")
    v = provider.get_detail('Properties', 'Aggregate Node CPU Cores')
    assert int(v) > 0, "Aggregate Node CPU Cores is 0"


def test_node_memory(provider):
    navigate_to(provider, 'Details')
    node_memory = provider.get_detail('Properties', 'Aggregate Node Memory')
    assert float(node_memory.split()[0]) > 0
