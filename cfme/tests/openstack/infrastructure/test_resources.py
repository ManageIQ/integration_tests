import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy +smartstate'),
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module')
]


@pytest.mark.regression
def test_number_of_cpu(provider, soft_assert):
    view_details = navigate_to(provider, 'Details')
    v = view_details.entities.summary('Properties').get_text_of('Aggregate Node CPU Resources')
    soft_assert(float(v.split()[0]) > 0, "Aggregate Node CPU Resources is 0")
    v = view_details.entities.summary('Properties').get_text_of('Aggregate Node CPUs')
    soft_assert(int(v) > 0, "Aggregate Node CPUs is 0")
    v = view_details.entities.summary('Properties').get_text_of('Aggregate Node CPU Cores')
    assert int(v) > 0, "Aggregate Node CPU Cores is 0"


@pytest.mark.regression
def test_node_memory(provider):
    view_details = navigate_to(provider, 'Details')
    node_memory = view_details.entities.summary('Properties').get_text_of('Aggregate Node Memory')
    assert float(node_memory.split()[0]) > 0
