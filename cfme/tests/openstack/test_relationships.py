"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""
from utils import testgen
import pytest


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_assinged_roles(provider):
    provider.load_details()
    result = provider.summary.relationships.deployment_roles.value

    assert result > 0


def test_nodes(provider):
    provider.load_details()
    result = provider.summary.relationships.nodes.value
    """
    todo get the list of VM's from external resource and compare
    it with result - currently not 0
    """

    assert result > 0


def test_templates(provider):
    provider.load_details()
    result = provider.summary.relationships.templates.value
    """
    todo get the list of images/templates from external resource and compare
    it with result - currently  5
    """

    assert result > 0


def test_stacks(provider):
    provider.load_details()
    result = provider.summary.relationships.orchestration_stacks.value
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert result > 0
