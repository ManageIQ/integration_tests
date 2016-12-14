"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""
import pytest
from utils import testgen
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


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
    it with result - currently  bigger than 0
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
