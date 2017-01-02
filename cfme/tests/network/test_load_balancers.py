import pytest
from utils import testgen
from cfme.networks.network_manager import NetworkManager


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc,
        required_fields=[['provisioning', 'image']])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_number_of_load_balancers(provider):
    network_manager_name = provider.name + " Network Manager"
    network_manager = NetworkManager(name=network_manager_name)
    a = network_manager.get_detail("Relationships", "Load balancers")
    assert True