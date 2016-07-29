from utils import testgen
import pytest


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")

def get_integer_value(x):
    return int(x.split(' ')[0])


@pytest.mark.usefixtures("setup_provider_modscope")
def test_number_of_cpu(provider, soft_assert):
    soft_assert(get_integer_value(
            provider.summary.properties.
                aggregate_node_cpu_resources.value) > 0,
                "Aggregate Node CPU Resources is 0")
    soft_assert(int(provider.summary.properties.
                    aggregate_node_cpus.value) > 0,
                "Aggregate Node CPU is 0")
    soft_assert(int(provider.summary.properties.
                    aggregate_node_cpu_cores.value) > 0,
                "Aggregate Node CPU Cores is 0")


def test_node_memory(provider, soft_assert):
    provider.load_details()
    soft_assert(get_integer_value(provider.summary.properties.
                                  aggregate_node_memory.value) > 0,
                "Aggregate Node Memory is 0")
