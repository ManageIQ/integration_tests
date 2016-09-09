from utils import testgen
import pytest

pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_number_of_cpu(provider, soft_assert):
    soft_assert((provider.summary.properties.aggregate_node_cpu_resources.
                 value.number) > 0, "Aggregate Node CPU Resources is 0")
    soft_assert((provider.summary.properties.aggregate_node_cpus.
                 value) > 0, "Aggregate Node CPU is 0")
    soft_assert((provider.summary.properties.aggregate_node_cpu_cores.
                 value) > 0, "Aggregate Node CPU Cores is 0")


def test_node_memory(provider):
    provider.load_details()
    assert (provider.summary.properties.aggregate_node_memory.
            value.number) > 0
