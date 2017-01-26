"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""
import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate'),
              pytest.mark.usefixtures("setup_provider_modscope")]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_assigned_roles(provider):
    navigate_to(provider, 'Details')
    assert int(provider.get_detail('Relationships', 'Deployment Roles')) > 0


def test_nodes(provider):
    provider.load_details()
    """
    todo get the list of VM's from external resource and compare
    it with result - currently not 0
    """

    assert int(provider.get_detail('Relationships', 'Nodes')) > 0


def test_templates(provider):
    navigate_to(provider, 'Details')
    """
    todo get the list of images/templates from external resource and compare
    it with result - currently  bigger than 0
    """

    assert int(provider.get_detail('Relationships', 'Templates')) > 0


def test_stacks(provider):
    navigate_to(provider, 'Details')
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert int(provider.get_detail('Relationships', 'Orchestration stacks')) > 0
