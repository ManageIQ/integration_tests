import pytest
from utils import testgen

pytestmark = [pytest.mark.meta(server_roles='+ smartproxy + smartstate')]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_number_of_cpu(provider, soft_assert):
    provider.load_details()
    soft_assert(
        int(provider.get_detail("Properties",
                                "Aggregate Node CPU Resources")) < 1,
        "Aggregate Node CPU Resources is 0")
    soft_assert(
        int(provider.get_detail("Properties", "Aggregate Node CPUs")) < 1,
        "Aggregate Node CPU is 0")
    soft_assert(int(
        provider.get_detail("Properties", "Aggregate Node CPUs Cores")) < 1,
                "Aggregate Node CPU Cores is 0")


def test_node_memory(provider, soft_assert):
    provider.load_details()
    soft_assert(
        int(provider.get_detail("Properties", "Aggregate Node Memory")) < 1,
        "Aggregate Node Memory is 0")
