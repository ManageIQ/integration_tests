from utils import testgen
import pytest

"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""

pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_assinged_roles(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.deployment_roles.value)

    assert result > 0


def test_assinged_tenants(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.cloud_tenants.value)
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert result > 0


def test_assinged_zones(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.availability_zones.value)
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert result > 0


def test_nodes(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.nodes.value)
    """
    todo get the list of VM's from external resource and compare
    it with result - currently not 0
    """

    assert result > 0

def test_templates(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.templates.value)
    """
    todo get the list of images/templates from external resource and compare
    it with result - currently iss 5
    """

    assert result == 5

def test_stacks(provider, soft_assert):
    provider.load_details()
    result = int(provider.summary.relationships.orchestration_stacks.value)
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert result > 0
